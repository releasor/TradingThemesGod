"""复盘台 run 跟踪与事件写入。"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from typing import Any, AsyncIterator

from app.repositories.review import ReviewRepository


class ReviewRunContext:
    def __init__(self, repo: ReviewRepository, run) -> None:
        self._repo = repo
        self._run = run
        self._partial = False
        self.source_status: dict[str, Any] = {}

    async def emit(
        self,
        event_type: str,
        entity_type: str,
        payload: dict[str, Any],
        entity_id: int | None = None,
    ) -> None:
        await self._repo.add_event(
            run_id=self._run.id,
            trade_date=self._run.trade_date,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload,
        )

    async def emit_strategy_card(self, payload: dict[str, Any]) -> None:
        await self.emit("strategy_card", "market", payload)

    async def emit_candidate(self, stock_id: int, payload: dict[str, Any]) -> None:
        await self.emit("candidate_upsert", "candidate", payload, entity_id=stock_id)

    async def emit_stage_change(self, theme_id: int, payload: dict[str, Any]) -> None:
        await self.emit("sector_stage_change", "theme", payload, entity_id=theme_id)

    async def emit_emotion(self, payload: dict[str, Any]) -> None:
        await self.emit("emotion_snapshot", "market", payload)

    async def emit_signal_batch(self, payload: dict[str, Any]) -> None:
        await self.emit("signal_batch", "batch", payload)

    async def emit_quote_refresh(self, payload: dict[str, Any]) -> None:
        await self.emit("quote_refresh", "batch", payload)

    def set_partial(self, source_status: dict[str, Any]) -> None:
        self._partial = True
        self.source_status.update(source_status)


class ReviewEventWriter:
    def __init__(self, repo: ReviewRepository) -> None:
        self.repo = repo

    @asynccontextmanager
    async def track(
        self,
        *,
        trade_date: date,
        run_type: str,
        request_meta: dict[str, Any] | None = None,
    ) -> AsyncIterator[ReviewRunContext]:
        run = await self.repo.create_run(
            trade_date=trade_date,
            run_type=run_type,
            request_meta=request_meta,
        )
        ctx = ReviewRunContext(self.repo, run)
        try:
            yield ctx
            status = "partial" if ctx._partial else "success"
            await self.repo.finish_run(
                run.id,
                status=status,
                source_status=ctx.source_status,
                error=None,
            )
        except Exception as exc:
            await self.repo.finish_run(
                run.id,
                status="failed",
                source_status=ctx.source_status,
                error=str(exc),
            )
            raise
