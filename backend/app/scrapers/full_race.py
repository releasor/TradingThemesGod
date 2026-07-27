"""全量多源竞速：并行 collect_full，仅胜出源 commit_full。

进程内内存状态（与调度器锁同级，不跨进程）。

Race status: racing | committing | completed | failed | cancelled
Phase: collecting | selecting | committing | done

取消语义：
- 尚未进入 committing：置 cancel、status=cancelled，不调用 commit_full。
- 已进入 committing：尽力而为（落库可能仍完成，无法安全中断）。
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


def _is_primary_valid(draft: FullScrapeDraft) -> bool:
    """主题与成分股均非空 → 可作为首选胜出草稿。"""
    return bool(draft.themes) and bool(draft.stocks_by_code)


def _is_fallback_only(draft: FullScrapeDraft) -> bool:
    """仅有题材、无成分股 → 仅作兜底（如 akshare themes-only）。"""
    return bool(draft.themes) and not draft.stocks_by_code


def default_full_race_sources() -> list[str]:
    """看板可选且实现 collect_full 的数据源。"""
    sources: list[str] = []
    for item in list_registered_scraper_sources(dashboard_only=True):
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


@dataclass
class RaceState:
    race_id: str
    sources: list[SourceRaceState]
    status: str = "racing"  # racing|committing|completed|failed|cancelled
    phase: str = "collecting"  # collecting|selecting|committing|done
    progress_pct: float = 0.0
    winner: str | None = None
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
                }
                for s in self.sources
            ],
            "winner": self.winner,
            "error": self.error,
            "items_scraped": self.items_scraped,
        }

    def source_map(self) -> dict[str, SourceRaceState]:
        return {s.id: s for s in self.sources}

    def refresh_collect_progress(self) -> None:
        if self.phase in ("committing", "done") or self.status == "committing":
            return
        progresses = [s.progress_pct for s in self.sources]
        self.progress_pct = max(progresses) if progresses else 0.0


class FullRaceManager:
    """进程内全量竞速管理器。"""

    def __init__(
        self,
        *,
        create_scraper: CreateScraperFn | None = None,
        persist_run: bool = True,
    ) -> None:
        self._races: dict[str, RaceState] = {}
        self._custom_factory = create_scraper is not None
        self._create_scraper = create_scraper or self._default_create_scraper
        self._persist_run = persist_run

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

        if state.phase != "committing" and state.status != "committing":
            # 尚未落库：标记取消，不 commit
            state.status = "cancelled"
            state.phase = "done"
            src_map = state.source_map()
            for source_id in state.cancel_events:
                src = src_map.get(source_id)
                if src is not None and src.status in ("pending", "running"):
                    src.status = "cancelled"
            state.refresh_collect_progress()
            logger.info("full_race_cancelled", race_id=race_id)
        else:
            # 已在 committing：尽力而为，落库可能仍完成
            logger.warning(
                "full_race_cancel_during_commit",
                race_id=race_id,
                note="already committing; commit may still finish",
            )

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
                        src.progress_pct = max(0.0, min(100.0, float(pct)))
                        if src.status == "running":
                            race.refresh_collect_progress()

                    return _on_progress

                task = asyncio.create_task(
                    scraper.collect_full(
                        cancel=cancel,
                        on_progress=_make_progress_cb(source_state, state),
                    ),
                    name=f"full-race-collect-{race_id}-{source}",
                )
                tasks[task] = source

            state.refresh_collect_progress()
            pending: set[asyncio.Task[FullScrapeDraft]] = set(tasks)
            fallbacks: list[tuple[str, FullScrapeDraft]] = []

            while pending:
                if state.cancel_requested and state.status == "cancelled":
                    for task in pending:
                        task.cancel()
                    if pending:
                        await asyncio.gather(*pending, return_exceptions=True)
                    return

                done, pending = await asyncio.wait(
                    pending, return_when=asyncio.FIRST_COMPLETED
                )

                for task in done:
                    source = tasks[task]
                    source_state = src_map[source]
                    try:
                        draft = task.result()
                    except asyncio.CancelledError:
                        source_state.status = "cancelled"
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

                    source_state.status = "completed"
                    source_state.progress_pct = 100.0
                    state.refresh_collect_progress()

                    if state.cancel_requested and state.status == "cancelled":
                        continue

                    if _is_primary_valid(draft):
                        await self._cancel_pending(pending, state)
                        pending.clear()
                        await self._commit_winner(
                            state, scrapers, source, draft
                        )
                        return

                    if _is_fallback_only(draft):
                        fallbacks.append((source, draft))
                        logger.info(
                            "full_race_fallback_held",
                            race_id=race_id,
                            source=source,
                            themes=len(draft.themes),
                        )
                        continue

                    source_state.status = "failed"
                    source_state.error = "empty draft (no themes)"
                    logger.info(
                        "full_race_collect_skipped",
                        race_id=race_id,
                        source=source,
                    )

            if state.cancel_requested or state.status == "cancelled":
                state.status = "cancelled"
                state.phase = "done"
                return

            if fallbacks:
                fallbacks.sort(key=lambda item: len(item[1].themes), reverse=True)
                source, draft = fallbacks[0]
                await self._commit_winner(state, scrapers, source, draft)
                return

            state.status = "failed"
            state.phase = "done"
            state.error = "all sources failed"
            state.progress_pct = max(state.progress_pct, 100.0)
            logger.error("full_race_all_failed", race_id=race_id)

        finally:
            for scraper in scrapers.values():
                close = getattr(scraper, "close", None)
                if close is None:
                    continue
                try:
                    await close()
                except Exception as exc:
                    logger.warning("full_race_scraper_close_failed", error=str(exc))

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

    async def _commit_winner(
        self,
        state: RaceState,
        scrapers: dict[str, Any],
        source: str,
        draft: FullScrapeDraft,
    ) -> None:
        if state.cancel_requested and state.status == "cancelled":
            logger.info(
                "full_race_skip_commit_cancelled",
                race_id=state.race_id,
                source=source,
            )
            return

        state.phase = "selecting"
        state.winner = source

        if state.cancel_requested and state.status == "cancelled":
            return

        state.status = "committing"
        state.phase = "committing"
        state.progress_pct = 70.0

        scraper = scrapers[source]
        try:
            items = await scraper.commit_full(draft)
            state.items_scraped = int(items)
            state.progress_pct = 100.0
            state.status = "completed"
            state.phase = "done"
            if self._persist_run:
                await self._record_scraper_run(source, int(items))
            logger.info(
                "full_race_completed",
                race_id=state.race_id,
                winner=source,
                items_scraped=items,
            )
        except Exception as exc:
            state.status = "failed"
            state.phase = "done"
            state.error = f"commit failed: {exc}"
            state.progress_pct = 100.0
            logger.error(
                "full_race_commit_failed",
                race_id=state.race_id,
                source=source,
                error=str(exc),
            )

    async def _record_scraper_run(self, source: str, items_scraped: int) -> None:
        """为胜出源写一条 completed scraper_run，供看板兼容。"""
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
