"""市场交易日历 API。"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.repositories.trading_calendar import DEFAULT_SOURCE
from app.schemas.trading_calendar import TradingCalendarResolve, TradingCalendarStatus
from app.services.trading_calendar import TradingCalendar, _shanghai_today
from app.services.trading_calendar_sync import (
    TradingCalendarSyncService,
    _remember_meta,
    _sync_lock,
    fetch_akshare_trade_dates,
    status_from_memory,
)

router = APIRouter(prefix="/market/calendar", tags=["market-calendar"])


@router.get("/status", response_model=TradingCalendarStatus)
async def get_calendar_status(db: AsyncSession = Depends(get_db)):
    """交易日历同步状态与当日解析结果。"""
    if not TradingCalendar.degraded and TradingCalendar._days:
        return status_from_memory()
    svc = TradingCalendarSyncService(db)
    await svc.ensure_memory_loaded()
    return await svc.build_status()


@router.get("/resolve", response_model=TradingCalendarResolve)
async def resolve_calendar_date(
    date_value: date | None = Query(default=None, alias="date", description="待解析日期"),
    db: AsyncSession = Depends(get_db),
):
    """将日期解析为最近开市日。"""
    if TradingCalendar.degraded or not TradingCalendar._days:
        svc = TradingCalendarSyncService(db)
        await svc.ensure_memory_loaded()
    input_date = date_value if date_value is not None else _shanghai_today()
    return TradingCalendarResolve(
        input_date=input_date,
        trade_date=TradingCalendar.resolve(date_value),
    )


@router.post("/sync", response_model=TradingCalendarStatus)
async def sync_calendar(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """强制从 AKShare 同步交易日历。网络拉取不长时间占用 DB 连接。"""
    async with _sync_lock:
        try:
            dates = await asyncio.to_thread(fetch_akshare_trade_dates)
        except Exception as exc:  # noqa: BLE001
            svc = TradingCalendarSyncService(db)
            await svc.repo.upsert_meta(last_error=str(exc)[:2000])
            await svc.reload_memory()
            await db.commit()
            status = status_from_memory()
            if not status.last_error:
                status = status.model_copy(update={"last_error": str(exc)[:2000]})
            return status

        svc = TradingCalendarSyncService(db)
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
        await db.commit()
        return status_from_memory()
