"""全量多源竞速：并行 collect_full，各源完成后立即 commit_full。

进程内内存状态（与调度器锁同级，不跨进程）。

Race status: racing | committing | completed | failed | cancelled
Phase: collecting | committing | done

取消语义：
- 已 commit 的源保留；未完成的源取消采集，不再 commit。
- 某源正在 commit 时取消：尽力而为（该源落库可能仍完成）。
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.domain.scraper_sources import list_registered_scraper_sources
from app.repositories.scraper_run import ScraperRunRepository
from app.scrapers.anti_scraping import AntiScrapingMiddleware
from app.scrapers.base import BaseScraper
from app.scrapers.draft_types import FullScrapeDraft
from app.scrapers.registry import scraper_registry

logger = get_logger(__name__)

CreateScraperFn = Callable[[str], Any]

# 单源采集硬超时：东财全量正常需 20–40 分钟，单源超过该时长视为卡死
FULL_RACE_SOURCE_TIMEOUT = 40 * 60.0
# 整体硬超时安全网：任何情况下竞速不超过该时长
FULL_RACE_OVERALL_TIMEOUT = 45 * 60.0


def _is_commit_worthy(draft: FullScrapeDraft) -> bool:
    """有题材即可落库（含成分股完整源与 themes-only 兜底）。"""
    return bool(draft.themes)


def _shorten_source_error(error: str | None, *, limit: int = 160) -> str:
    """将底层异常压缩为可读短句（连接超时、HTTP 状态等）。"""
    text = (error or "").strip()
    if not text:
        return "未知错误"
    lower = text.lower()
    if "remotedisconnected" in lower or "connection aborted" in lower:
        return "上游提前断开连接"
    if "connecttimeout" in lower or "connect timeout" in lower or "timed out" in lower:
        host = ""
        for marker in ("host='", 'host="', "host="):
            idx = lower.find(marker)
            if idx >= 0:
                start = idx + len(marker)
                end = start
                while end < len(text) and text[end] not in "', )":
                    end += 1
                host = text[start:end]
                break
        return f"连接超时{f'（{host}）' if host else ''}"
    if "max retries exceeded" in lower:
        return "请求重试耗尽（上游不可达）"
    if "proxyerror" in lower or ("proxy" in lower and "error" in lower):
        return "代理/网络错误"
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _aggregate_source_errors(sources: list[SourceRaceState]) -> str:
    """汇总各源失败原因，供 race.error 与前端展示。"""
    parts: list[str] = []
    for src in sources:
        if src.status == "failed":
            parts.append(f"{src.id}: {_shorten_source_error(src.error)}")
        elif src.status not in ("completed", "cancelled") and src.error:
            parts.append(f"{src.id}: {_shorten_source_error(src.error)}")
    if parts:
        return "全部数据源失败 — " + "；".join(parts)
    return "全部数据源失败"


def default_full_race_sources() -> list[str]:
    """看板可选且实现 collect_full 的数据源。"""
    from app.services.tushare_settings import get_cached_tushare_runtime

    runtime = get_cached_tushare_runtime()
    sources: list[str] = []
    for item in list_registered_scraper_sources(dashboard_only=True):
        if item.id == "tushare" and not runtime.ready:
            continue
        cls = scraper_registry.get(item.id)
        if cls is not None and callable(getattr(cls, "collect_full", None)):
            sources.append(item.id)
    return sources


@dataclass
class SourceRaceState:
    id: str
    status: str = "pending"  # pending|running|completed|failed|cancelled
    progress_pct: float = 0.0
    error: str | None = None
    items_scraped: int | None = None


@dataclass
class RaceState:
    race_id: str
    sources: list[SourceRaceState]
    status: str = "racing"  # racing|committing|completed|failed|cancelled
    phase: str = "collecting"  # collecting|committing|done
    progress_pct: float = 0.0
    winner: str | None = None  # 首个成功 commit 的源（兼容旧字段）
    committed_sources: list[str] = field(default_factory=list)
    error: str | None = None
    items_scraped: int | None = None
    cancel_requested: bool = False
    cancel_events: dict[str, asyncio.Event] = field(default_factory=dict)
    task: asyncio.Task[None] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "race_id": self.race_id,
            "status": self.status,
            "phase": self.phase,
            "progress_pct": self.progress_pct,
            "sources": [
                {
                    "id": s.id,
                    "status": s.status,
                    "progress_pct": s.progress_pct,
                    "error": s.error,
                    "items_scraped": s.items_scraped,
                }
                for s in self.sources
            ],
            "winner": self.winner,
            "committed_sources": list(self.committed_sources),
            "error": self.error,
            "items_scraped": self.items_scraped,
        }

    def source_map(self) -> dict[str, SourceRaceState]:
        return {s.id: s for s in self.sources}

    def refresh_progress(self) -> None:
        """按各源进度刷新整体进度；全部终态时为 100。"""
        if self.phase == "done":
            self.progress_pct = 100.0
            return
        pcts = [s.progress_pct for s in self.sources]
        self.progress_pct = sum(pcts) / len(pcts) if pcts else 0.0


class FullRaceManager:
    """进程内全量竞速管理器。"""

    def __init__(
        self,
        *,
        create_scraper: CreateScraperFn | None = None,
        persist_run: bool = True,
        source_timeout: float = FULL_RACE_SOURCE_TIMEOUT,
        overall_timeout: float = FULL_RACE_OVERALL_TIMEOUT,
        # 兼容旧测试参数名（已忽略）
        fallback_grace: float | None = None,
    ) -> None:
        self._races: dict[str, RaceState] = {}
        self._custom_factory = create_scraper is not None
        self._create_scraper = create_scraper or self._default_create_scraper
        self._persist_run = persist_run
        self._source_timeout = source_timeout
        self._overall_timeout = overall_timeout
        _ = fallback_grace

    @staticmethod
    def _default_create_scraper(source: str) -> BaseScraper:
        scraper_cls = scraper_registry.get(source)
        if scraper_cls is None:
            raise ValueError(f"未注册的数据源: {source}")
        return scraper_cls(middleware=AntiScrapingMiddleware())

    async def start(self, sources: list[str] | None = None) -> str:
        """启动竞速，返回 race_id。"""
        return await self.start_full_race(sources)

    def get(self, race_id: str) -> dict[str, Any]:
        return self.get_race(race_id)

    async def cancel(self, race_id: str) -> dict[str, Any]:
        return await self.cancel_race(race_id)

    async def start_full_race(self, sources: list[str] | None = None) -> str:
        # 全量前从 DB 刷新 Tushare 缓存，确保设置页刚保存的启用/Token 立刻生效
        if sources is None:
            try:
                from app.services.tushare_settings import TushareSettingsService

                async with AsyncSessionLocal() as session:
                    await TushareSettingsService(session).resolve_runtime()
            except Exception as exc:  # noqa: BLE001
                logger.warning("full_race_tushare_cache_refresh_failed", error=str(exc))

        resolved = list(sources) if sources else default_full_race_sources()
        if not resolved:
            raise ValueError("没有可用的全量竞速数据源")

        if not self._custom_factory:
            for source in resolved:
                cls = scraper_registry.get(source)
                if cls is None:
                    raise ValueError(f"未注册的数据源: {source}")
                if not callable(getattr(cls, "collect_full", None)):
                    raise ValueError(f"数据源不支持全量竞速: {source}")

        race_id = uuid.uuid4().hex
        state = RaceState(
            race_id=race_id,
            sources=[SourceRaceState(id=s) for s in resolved],
        )
        for source in resolved:
            state.cancel_events[source] = asyncio.Event()

        self._races[race_id] = state
        state.task = asyncio.create_task(
            self._execute_race(race_id),
            name=f"full-race-{race_id}",
        )
        state.task.add_done_callback(
            lambda t: self._handle_race_done(race_id, t),
        )
        logger.info("full_race_started", race_id=race_id, sources=resolved)
        return race_id

    def get_race(self, race_id: str) -> dict[str, Any]:
        state = self._races.get(race_id)
        if state is None:
            raise KeyError(race_id)
        return state.to_dict()

    async def cancel_race(self, race_id: str) -> dict[str, Any]:
        state = self._races.get(race_id)
        if state is None:
            raise KeyError(race_id)

        state.cancel_requested = True
        for event in state.cancel_events.values():
            event.set()

        if state.status in ("completed", "failed", "cancelled"):
            return state.to_dict()

        # 尚未全部结束：标记取消；已 commit 的源保持 completed
        if state.phase != "done":
            src_map = state.source_map()
            for source_id in state.cancel_events:
                src = src_map.get(source_id)
                if src is not None and src.status in ("pending", "running"):
                    src.status = "cancelled"
            if state.committed_sources:
                # 已有落库：竞速视为成功完成（部分取消）
                state.status = "completed"
                state.phase = "done"
                state.progress_pct = 100.0
                logger.info(
                    "full_race_cancelled_after_partial_commit",
                    race_id=race_id,
                    committed=state.committed_sources,
                )
            else:
                state.status = "cancelled"
                state.phase = "done"
                state.refresh_progress()
                logger.info("full_race_cancelled", race_id=race_id)

        return state.to_dict()

    def _handle_race_done(self, race_id: str, task: asyncio.Task[None]) -> None:
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            logger.error("full_race_task_error", race_id=race_id, error=str(exc))
            state = self._races.get(race_id)
            if state is not None and state.status == "racing":
                state.status = "failed"
                state.phase = "done"
                state.error = str(exc)

    async def _execute_race(self, race_id: str) -> None:
        state = self._races[race_id]
        scrapers: dict[str, Any] = {}
        tasks: dict[asyncio.Task[FullScrapeDraft], str] = {}
        src_map = state.source_map()

        try:
            for source_state in state.sources:
                source = source_state.id
                scraper = self._create_scraper(source)
                scrapers[source] = scraper
                source_state.status = "running"
                source_state.progress_pct = 0.0
                cancel = state.cancel_events[source]

                def _make_progress_cb(
                    src: SourceRaceState, race: RaceState
                ) -> Callable[[float], None]:
                    def _on_progress(pct: float) -> None:
                        # 采集进度占 0–90，留 10% 给 commit
                        src.progress_pct = max(0.0, min(90.0, float(pct) * 0.9))
                        if src.status == "running":
                            race.refresh_progress()

                    return _on_progress

                task = asyncio.create_task(
                    self._collect_with_timeout(
                        scraper,
                        source,
                        cancel=cancel,
                        on_progress=_make_progress_cb(source_state, state),
                    ),
                    name=f"full-race-collect-{race_id}-{source}",
                )
                tasks[task] = source

            state.refresh_progress()
            pending: set[asyncio.Task[FullScrapeDraft]] = set(tasks)
            loop = asyncio.get_running_loop()
            overall_deadline = loop.time() + self._overall_timeout

            while pending:
                if state.cancel_requested and state.phase == "done":
                    for task in pending:
                        task.cancel()
                    if pending:
                        await asyncio.gather(*pending, return_exceptions=True)
                    return

                wait_timeout = max(0.0, overall_deadline - loop.time())
                done, pending = await asyncio.wait(
                    pending,
                    timeout=wait_timeout,
                    return_when=asyncio.FIRST_COMPLETED,
                )

                for task in done:
                    source = tasks[task]
                    source_state = src_map[source]
                    try:
                        draft = task.result()
                    except asyncio.CancelledError:
                        if source_state.status == "running":
                            source_state.status = "cancelled"
                        continue
                    except asyncio.TimeoutError:
                        source_state.status = "failed"
                        source_state.error = (
                            f"采集超时（单源超过 "
                            f"{int(self._source_timeout // 60)} 分钟未完成）"
                        )
                        source_state.progress_pct = 100.0
                        logger.warning(
                            "full_race_collect_timeout",
                            race_id=race_id,
                            source=source,
                            timeout=self._source_timeout,
                        )
                        continue
                    except Exception as exc:
                        source_state.status = "failed"
                        source_state.error = str(exc)
                        source_state.progress_pct = 100.0
                        logger.warning(
                            "full_race_collect_failed",
                            race_id=race_id,
                            source=source,
                            error=str(exc),
                        )
                        continue

                    if state.cancel_requested and state.phase == "done":
                        if source_state.status == "running":
                            source_state.status = "cancelled"
                        continue

                    if not _is_commit_worthy(draft):
                        source_state.status = "failed"
                        source_state.error = "empty draft (no themes)"
                        source_state.progress_pct = 100.0
                        logger.info(
                            "full_race_collect_skipped",
                            race_id=race_id,
                            source=source,
                        )
                        continue

                    # 各源采集完成后立即 commit，互不等待
                    await self._commit_source(state, scrapers, source, draft)

                now = loop.time()
                if now >= overall_deadline and pending:
                    logger.error(
                        "full_race_overall_timeout",
                        race_id=race_id,
                        timeout=self._overall_timeout,
                        pending_sources=[tasks[t] for t in pending],
                    )
                    await self._cancel_pending(pending, state)
                    pending.clear()
                    for src in state.sources:
                        if src.status in ("pending", "running", "cancelled"):
                            if src.id not in state.committed_sources:
                                src.status = "failed"
                                src.error = (
                                    f"采集超时（全量竞速超过 "
                                    f"{int(self._overall_timeout // 60)} 分钟未完成）"
                                )
                                src.progress_pct = 100.0
                    break

                state.refresh_progress()

            if state.phase == "done":
                return

            if state.committed_sources:
                state.status = "completed"
                state.phase = "done"
                state.progress_pct = 100.0
                state.items_scraped = sum(
                    s.items_scraped or 0
                    for s in state.sources
                    if s.id in state.committed_sources
                )
                logger.info(
                    "full_race_completed",
                    race_id=race_id,
                    committed=state.committed_sources,
                    items_scraped=state.items_scraped,
                )
                return

            if state.cancel_requested:
                state.status = "cancelled"
                state.phase = "done"
                return

            state.status = "failed"
            state.phase = "done"
            state.error = _aggregate_source_errors(state.sources)
            state.progress_pct = 100.0
            logger.error(
                "full_race_all_failed",
                race_id=race_id,
                error=state.error,
            )

        finally:
            for scraper in scrapers.values():
                close = getattr(scraper, "close", None)
                if close is None:
                    continue
                try:
                    await close()
                except Exception as exc:
                    logger.warning("full_race_scraper_close_failed", error=str(exc))

    async def _collect_with_timeout(
        self,
        scraper: Any,
        source: str,
        *,
        cancel: asyncio.Event,
        on_progress: Callable[[float], None],
    ) -> FullScrapeDraft:
        """包一层单源硬超时：源卡死时抛 TimeoutError，不拖死整个竞速。"""
        return await asyncio.wait_for(
            scraper.collect_full(cancel=cancel, on_progress=on_progress),
            timeout=self._source_timeout,
        )

    async def _cancel_pending(
        self,
        pending: set[asyncio.Task[FullScrapeDraft]],
        state: RaceState,
    ) -> None:
        for event in state.cancel_events.values():
            event.set()
        for task in pending:
            if not task.done():
                task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        src_map = state.source_map()
        for _source_id, src in src_map.items():
            if src.status in ("pending", "running"):
                src.status = "cancelled"

    async def _commit_source(
        self,
        state: RaceState,
        scrapers: dict[str, Any],
        source: str,
        draft: FullScrapeDraft,
    ) -> None:
        source_state = state.source_map()[source]
        if (
            state.cancel_requested
            and state.phase == "done"
            and not state.committed_sources
        ):
            source_state.status = "cancelled"
            logger.info(
                "full_race_skip_commit_cancelled",
                race_id=state.race_id,
                source=source,
            )
            return

        state.status = "committing"
        state.phase = "committing"
        source_state.progress_pct = max(source_state.progress_pct, 90.0)
        state.refresh_progress()

        scraper = scrapers[source]
        try:
            items = await scraper.commit_full(draft)
            items_i = int(items)
            source_state.status = "completed"
            source_state.progress_pct = 100.0
            source_state.items_scraped = items_i
            source_state.error = None
            if source not in state.committed_sources:
                state.committed_sources.append(source)
            if state.winner is None:
                state.winner = source
            state.items_scraped = (state.items_scraped or 0) + items_i
            # 仍有其他源在跑时保持 racing/collecting，全部结束后再 completed
            still_running = any(
                s.status in ("pending", "running") for s in state.sources
            )
            if still_running:
                state.status = "racing"
                state.phase = "collecting"
            if self._persist_run:
                await self._record_scraper_run(source, items_i)
            logger.info(
                "full_race_source_committed",
                race_id=state.race_id,
                source=source,
                items_scraped=items_i,
                has_stocks=bool(draft.stocks_by_code),
            )
        except Exception as exc:
            source_state.status = "failed"
            source_state.error = f"commit failed: {exc}"
            source_state.progress_pct = 100.0
            logger.error(
                "full_race_commit_failed",
                race_id=state.race_id,
                source=source,
                error=str(exc),
            )
        finally:
            state.refresh_progress()

    async def _record_scraper_run(self, source: str, items_scraped: int) -> None:
        """为成功 commit 的源写一条 completed scraper_run。"""
        try:
            async with AsyncSessionLocal() as session:
                repo = ScraperRunRepository(session)
                run = await repo.create(source)
                await repo.update_status(
                    run_id=run.id,
                    status="completed",
                    items_scraped=items_scraped,
                )
                await session.commit()
        except Exception as exc:
            logger.warning(
                "full_race_scraper_run_record_failed",
                source=source,
                error=str(exc),
            )


# 全局管理器
full_race_manager = FullRaceManager()


async def start_full_race(sources: list[str] | None = None) -> str:
    return await full_race_manager.start_full_race(sources)


async def get_race(race_id: str) -> dict:
    return full_race_manager.get_race(race_id)


async def cancel_race(race_id: str) -> dict:
    return await full_race_manager.cancel_race(race_id)
