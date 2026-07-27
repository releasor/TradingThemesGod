"""从 AKShare 同步 A 股开市日到数据库并刷新内存日历。"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.repositories.trading_calendar import DEFAULT_SOURCE, TradingCalendarRepository
from app.schemas.trading_calendar import TradingCalendarStatus
from app.services.trading_calendar import TradingCalendar, _shanghai_today

logger = get_logger(__name__)

SYNC_MAX_AGE = timedelta(hours=24)
_sync_lock = asyncio.Lock()

# 进程内缓存的 meta，避免 status 每次打库
_meta_cache: dict[str, object | None] = {
    "source": DEFAULT_SOURCE,
    "last_synced_at": None,
    "row_count": 0,
    "min_date": None,
    "max_date": None,
    "last_error": None,
}


def fetch_akshare_trade_dates() -> list[date]:
    import akshare as ak

    frame = ak.tool_trade_date_hist_sina()
    if frame is None or getattr(frame, "empty", True):
        raise RuntimeError("AKShare 交易日历为空")
    col = "trade_date" if "trade_date" in frame.columns else frame.columns[0]
    out: list[date] = []
    for raw in frame[col].tolist():
        if isinstance(raw, date) and not isinstance(raw, datetime):
            out.append(raw)
            continue
        text = str(raw).strip()[:10]
        out.append(date.fromisoformat(text))
    if not out:
        raise RuntimeError("AKShare 交易日历解析后为空")
    return sorted(set(out))


def _remember_meta(
    *,
    source: str = DEFAULT_SOURCE,
    last_synced_at: datetime | None = None,
    row_count: int = 0,
    min_date: date | None = None,
    max_date: date | None = None,
    last_error: str | None = None,
) -> None:
    _meta_cache["source"] = source
    _meta_cache["last_synced_at"] = last_synced_at
    _meta_cache["row_count"] = row_count
    _meta_cache["min_date"] = min_date
    _meta_cache["max_date"] = max_date
    _meta_cache["last_error"] = last_error


def status_from_memory() -> TradingCalendarStatus:
    today = _shanghai_today()
    degraded = TradingCalendar.degraded
    missing = ["trading_calendar"] if degraded else []
    return TradingCalendarStatus(
        source=str(_meta_cache.get("source") or DEFAULT_SOURCE),
        last_synced_at=_meta_cache.get("last_synced_at"),  # type: ignore[arg-type]
        row_count=int(_meta_cache.get("row_count") or len(TradingCalendar._days)),
        min_date=_meta_cache.get("min_date"),  # type: ignore[arg-type]
        max_date=_meta_cache.get("max_date"),  # type: ignore[arg-type]
        last_error=_meta_cache.get("last_error"),  # type: ignore[arg-type]
        degraded=degraded,
        today_is_trade_day=TradingCalendar.is_trade_day(today),
        data_trade_date=TradingCalendar.resolve(today),
        missing_sources=missing,
    )


class TradingCalendarSyncService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = TradingCalendarRepository(session)

    async def reload_memory(self) -> None:
        dates = await self.repo.list_all_dates()
        TradingCalendar.load_dates(set(dates))
        meta = await self.repo.get_meta()
        if meta is not None:
            _remember_meta(
                source=meta.source,
                last_synced_at=meta.last_synced_at,
                row_count=meta.row_count,
                min_date=meta.min_date,
                max_date=meta.max_date,
                last_error=meta.last_error,
            )

    async def ensure_memory_loaded(self) -> None:
        """仅在内存为空时从 DB 加载，避免每次请求扫全表。"""
        if not TradingCalendar.degraded and TradingCalendar._days:
            return
        await self.reload_memory()

    async def build_status(self) -> TradingCalendarStatus:
        meta = await self.repo.get_meta()
        if meta is not None:
            _remember_meta(
                source=meta.source,
                last_synced_at=meta.last_synced_at,
                row_count=meta.row_count,
                min_date=meta.min_date,
                max_date=meta.max_date,
                last_error=meta.last_error,
            )
        return status_from_memory()

    async def sync(self, *, force: bool = False) -> TradingCalendarStatus:
        async with _sync_lock:
            return await self._sync_unlocked(force=force)

    async def _sync_unlocked(self, *, force: bool) -> TradingCalendarStatus:
        meta = await self.repo.get_meta()
        now = datetime.now(timezone.utc)

        if not force and meta is not None and meta.last_synced_at is not None and meta.row_count > 0:
            synced_at = meta.last_synced_at
            if synced_at.tzinfo is None:
                synced_at = synced_at.replace(tzinfo=timezone.utc)
            if now - synced_at < SYNC_MAX_AGE:
                await self.reload_memory()
                return await self.build_status()

        try:
            dates = await asyncio.to_thread(fetch_akshare_trade_dates)
            count = await self.repo.replace_all(dates, source=DEFAULT_SOURCE)
            await self.repo.upsert_meta(
                source=DEFAULT_SOURCE,
                last_synced_at=now,
                row_count=count,
                min_date=min(dates) if dates else None,
                max_date=max(dates) if dates else None,
                clear_error=True,
            )
            TradingCalendar.load_dates(set(dates))
            _remember_meta(
                source=DEFAULT_SOURCE,
                last_synced_at=now,
                row_count=count,
                min_date=min(dates) if dates else None,
                max_date=max(dates) if dates else None,
                last_error=None,
            )
            return status_from_memory()
        except Exception as exc:  # noqa: BLE001
            logger.warning("交易日历同步失败", error=str(exc))
            await self.repo.upsert_meta(
                source=DEFAULT_SOURCE,
                row_count=(meta.row_count if meta else 0),
                min_date=(meta.min_date if meta else None),
                max_date=(meta.max_date if meta else None),
                last_error=str(exc)[:2000],
            )
            await self.reload_memory()
            status = status_from_memory()
            if not status.last_error:
                status = status.model_copy(update={"last_error": str(exc)[:2000]})
            return status

    async def maybe_sync_on_startup(self) -> None:
        try:
            await self.sync(force=False)
        except Exception as exc:  # noqa: BLE001
            logger.warning("交易日历启动同步失败", error=str(exc))
            try:
                await self.reload_memory()
            except Exception as reload_exc:  # noqa: BLE001
                logger.warning("交易日历内存加载失败", error=str(reload_exc))


async def startup_sync_calendar() -> None:
    """启动同步：网络拉取不占用 DB 连接。"""
    from app.core.database import AsyncSessionLocal

    async with _sync_lock:
        # 先看库内是否已有且未过期
        async with AsyncSessionLocal() as session:
            repo = TradingCalendarRepository(session)
            meta = await repo.get_meta()
            now = datetime.now(timezone.utc)
            if (
                meta is not None
                and meta.last_synced_at is not None
                and meta.row_count > 0
            ):
                synced_at = meta.last_synced_at
                if synced_at.tzinfo is None:
                    synced_at = synced_at.replace(tzinfo=timezone.utc)
                if now - synced_at < SYNC_MAX_AGE:
                    dates = await repo.list_all_dates()
                    TradingCalendar.load_dates(set(dates))
                    _remember_meta(
                        source=meta.source,
                        last_synced_at=meta.last_synced_at,
                        row_count=meta.row_count,
                        min_date=meta.min_date,
                        max_date=meta.max_date,
                        last_error=meta.last_error,
                    )
                    await session.commit()
                    return

        # 无会话拉网
        try:
            dates = await asyncio.to_thread(fetch_akshare_trade_dates)
        except Exception as exc:  # noqa: BLE001
            logger.warning("交易日历启动拉取失败", error=str(exc))
            async with AsyncSessionLocal() as session:
                svc = TradingCalendarSyncService(session)
                await svc.repo.upsert_meta(last_error=str(exc)[:2000])
                await svc.reload_memory()
                await session.commit()
            return

        async with AsyncSessionLocal() as session:
            svc = TradingCalendarSyncService(session)
            now = datetime.now(timezone.utc)
            count = await svc.repo.replace_all(dates, source=DEFAULT_SOURCE)
            await svc.repo.upsert_meta(
                source=DEFAULT_SOURCE,
                last_synced_at=now,
                row_count=count,
                min_date=min(dates) if dates else None,
                max_date=max(dates) if dates else None,
                clear_error=True,
            )
            TradingCalendar.load_dates(set(dates))
            _remember_meta(
                source=DEFAULT_SOURCE,
                last_synced_at=now,
                row_count=count,
                min_date=min(dates) if dates else None,
                max_date=max(dates) if dates else None,
                last_error=None,
            )
            await session.commit()
