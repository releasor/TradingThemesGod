"""复盘台 run/event/report 仓储。"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import distinct, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review import ReviewAiReport, ReviewEvent, ReviewRun


class ReviewRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_run(
        self,
        *,
        trade_date: date,
        run_type: str,
        request_meta: dict[str, Any] | None = None,
    ) -> ReviewRun:
        run = ReviewRun(
            trade_date=trade_date,
            run_type=run_type,
            status="running",
            source_status={},
            request_meta=request_meta or {},
            started_at=datetime.now(timezone.utc),
        )
        self.session.add(run)
        await self.session.flush()
        return run

    async def finish_run(
        self,
        run_id: int,
        *,
        status: str,
        source_status: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        run = await self.session.scalar(
            select(ReviewRun).where(ReviewRun.id == run_id)
        )
        if run is None:
            return

        run.status = status
        run.finished_at = datetime.now(timezone.utc)

        merged = dict(run.source_status or {})
        if source_status:
            merged.update(source_status)
        if error is not None:
            merged["error"] = error
        run.source_status = merged

        await self.session.flush()

    async def add_event(
        self,
        *,
        run_id: int | None,
        trade_date: date,
        event_type: str,
        entity_type: str,
        entity_id: int | None,
        payload: dict[str, Any],
        occurred_at: datetime | None = None,
    ) -> ReviewEvent:
        event = ReviewEvent(
            run_id=run_id,
            trade_date=trade_date,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            payload_json=payload,
            occurred_at=occurred_at or datetime.now(timezone.utc),
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def list_runs(self, trade_date: date) -> list[ReviewRun]:
        result = await self.session.scalars(
            select(ReviewRun)
            .where(ReviewRun.trade_date == trade_date)
            .order_by(ReviewRun.started_at.asc())
        )
        return list(result.all())

    async def list_events(
        self, trade_date: date, event_types: list[str] | None = None
    ) -> list[ReviewEvent]:
        stmt = (
            select(ReviewEvent)
            .where(ReviewEvent.trade_date == trade_date)
            .order_by(ReviewEvent.occurred_at.asc())
        )
        if event_types:
            stmt = stmt.where(ReviewEvent.event_type.in_(event_types))
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def list_theme_events(
        self, theme_id: int, start: date, end: date
    ) -> list[ReviewEvent]:
        theme_entity = (ReviewEvent.entity_type == "theme") & (
            ReviewEvent.entity_id == theme_id
        )
        payload_theme = ReviewEvent.payload_json["theme_id"].as_integer() == theme_id
        stmt = (
            select(ReviewEvent)
            .where(
                ReviewEvent.trade_date >= start,
                ReviewEvent.trade_date <= end,
                or_(theme_entity, payload_theme),
            )
            .order_by(ReviewEvent.trade_date.asc(), ReviewEvent.occurred_at.asc())
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def list_trade_dates(self, start: date, end: date) -> list[date]:
        result = await self.session.scalars(
            select(distinct(ReviewRun.trade_date))
            .where(ReviewRun.trade_date >= start, ReviewRun.trade_date <= end)
            .order_by(ReviewRun.trade_date.asc())
        )
        return list(result.all())

    async def get_report(
        self, trade_date: date, user_id: int | None
    ) -> ReviewAiReport | None:
        stmt = select(ReviewAiReport).where(ReviewAiReport.trade_date == trade_date)
        if user_id is None:
            stmt = stmt.where(ReviewAiReport.user_id.is_(None)).order_by(
                ReviewAiReport.updated_at.desc()
            )
        else:
            stmt = stmt.where(ReviewAiReport.user_id == user_id)
        return await self.session.scalar(stmt.limit(1))

    async def upsert_report(
        self,
        *,
        trade_date: date,
        user_id: int | None,
        status: str,
        content_md: str = "",
        content_json: dict[str, Any] | None = None,
        model_name: str | None = None,
        error: str | None = None,
        source_run_ids: list[Any] | None = None,
    ) -> ReviewAiReport:
        stmt = select(ReviewAiReport).where(ReviewAiReport.trade_date == trade_date)
        if user_id is None:
            stmt = stmt.where(ReviewAiReport.user_id.is_(None))
        else:
            stmt = stmt.where(ReviewAiReport.user_id == user_id)

        row = await self.session.scalar(stmt)
        if row is None:
            row = ReviewAiReport(
                trade_date=trade_date,
                user_id=user_id,
            )
            self.session.add(row)

        row.status = status
        row.content_md = content_md
        row.content_json = content_json or {}
        row.model_name = model_name
        row.error = error
        row.source_run_ids = source_run_ids or []
        await self.session.flush()
        return row
