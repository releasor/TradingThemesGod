"""催化雷达数据访问。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.theme_insights import build_event_key
from app.models.catalyst import CatalystClassification
from app.models.news_article import NewsArticle
from app.models.theme import Theme
from app.models.theme_driver_event import ThemeDriverEvent
from app.repositories.base import BaseRepository
from app.services.catalyst_rules import (
    REPLAY_WINDOW_DAYS,
    ClassifyResult,
    EventInput,
    classify_event,
)


@dataclass(frozen=True, slots=True)
class FeedRow:
    """催化 feed 查询行。"""

    event_id: int
    theme_id: int
    theme_name: str
    title: str
    summary: str
    source: str
    url: str
    published_at: datetime
    relevance_score: int
    freshness: str
    actor_type: str
    classified_by: str | None


class CatalystRepository(BaseRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def apply_classification(
        self,
        event_id: int,
        result: ClassifyResult,
        *,
        method: str,
        model_name: str | None = None,
    ) -> None:
        event = await self.session.get(ThemeDriverEvent, event_id)
        if event is None:
            return
        now = datetime.now(UTC)
        event.freshness = result.freshness
        event.actor_type = result.actor_type
        event.classified_by = method
        event.classified_at = now
        self.session.add(
            CatalystClassification(
                event_id=event_id,
                freshness=result.freshness,
                actor_type=result.actor_type,
                method=method,
                model_name=model_name,
                confidence=result.confidence,
                rationale=result.rationale,
            )
        )
        await self.session.flush()

    def _feed_query(
        self,
        *,
        freshness: str | None = None,
        actor_type: str | None = None,
        theme_id: int | None = None,
        q: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ):
        query = (
            select(
                ThemeDriverEvent.id.label("event_id"),
                ThemeDriverEvent.theme_id,
                Theme.name.label("theme_name"),
                ThemeDriverEvent.title,
                ThemeDriverEvent.summary,
                ThemeDriverEvent.source,
                ThemeDriverEvent.url,
                ThemeDriverEvent.published_at,
                ThemeDriverEvent.relevance_score,
                ThemeDriverEvent.freshness,
                ThemeDriverEvent.actor_type,
                ThemeDriverEvent.classified_by,
            )
            .join(Theme, Theme.id == ThemeDriverEvent.theme_id)
            .where(Theme.deleted_at.is_(None))
        )
        if freshness:
            query = query.where(ThemeDriverEvent.freshness == freshness)
        if actor_type:
            query = query.where(ThemeDriverEvent.actor_type == actor_type)
        if theme_id is not None:
            query = query.where(ThemeDriverEvent.theme_id == theme_id)
        if q:
            pattern = f"%{q.strip()}%"
            query = query.where(
                or_(
                    ThemeDriverEvent.title.like(pattern),
                    ThemeDriverEvent.summary.like(pattern),
                )
            )
        if start is not None:
            query = query.where(ThemeDriverEvent.published_at >= start)
        if end is not None:
            query = query.where(ThemeDriverEvent.published_at <= end)
        return query

    @staticmethod
    def _row_to_feed(row) -> FeedRow:
        return FeedRow(
            event_id=row.event_id,
            theme_id=row.theme_id,
            theme_name=row.theme_name,
            title=row.title,
            summary=row.summary,
            source=row.source,
            url=row.url,
            published_at=row.published_at,
            relevance_score=row.relevance_score,
            freshness=row.freshness,
            actor_type=row.actor_type,
            classified_by=row.classified_by,
        )

    async def list_feed(
        self,
        *,
        freshness: str | None = None,
        actor_type: str | None = None,
        theme_id: int | None = None,
        q: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 30,
        offset: int = 0,
    ) -> list[FeedRow]:
        query = self._feed_query(
            freshness=freshness,
            actor_type=actor_type,
            theme_id=theme_id,
            q=q,
            start=start,
            end=end,
        )
        result = await self.session.execute(
            query.order_by(desc(ThemeDriverEvent.published_at))
            .offset(offset)
            .limit(limit)
        )
        return [self._row_to_feed(row) for row in result.all()]

    async def count_feed(
        self,
        *,
        freshness: str | None = None,
        actor_type: str | None = None,
        theme_id: int | None = None,
        q: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> int:
        query = self._feed_query(
            freshness=freshness,
            actor_type=actor_type,
            theme_id=theme_id,
            q=q,
            start=start,
            end=end,
        )
        count = await self.session.scalar(
            select(func.count()).select_from(query.subquery())
        )
        return count or 0

    async def count_by_theme(self, theme_id: int, since: datetime) -> dict[str, int]:
        result = await self.session.execute(
            select(
                ThemeDriverEvent.freshness,
                ThemeDriverEvent.actor_type,
                func.count(),
            )
            .where(
                ThemeDriverEvent.theme_id == theme_id,
                ThemeDriverEvent.published_at >= since,
            )
            .group_by(ThemeDriverEvent.freshness, ThemeDriverEvent.actor_type)
        )
        counts: dict[str, int] = {}
        for freshness, actor, total in result.all():
            counts[freshness] = counts.get(freshness, 0) + total
            counts[actor] = counts.get(actor, 0) + total
        return counts

    async def list_theme_events(
        self, theme_id: int, limit: int = 10
    ) -> list[ThemeDriverEvent]:
        result = await self.session.scalars(
            select(ThemeDriverEvent)
            .where(ThemeDriverEvent.theme_id == theme_id)
            .order_by(desc(ThemeDriverEvent.published_at))
            .limit(limit)
        )
        return list(result.all())

    async def list_news_headlines_for_theme(
        self, theme_name: str, limit: int = 8
    ) -> list[NewsArticle]:
        if not theme_name.strip():
            return []
        result = await self.session.scalars(
            select(NewsArticle)
            .where(NewsArticle.title.contains(theme_name.strip()))
            .order_by(desc(NewsArticle.published_at))
            .limit(limit)
        )
        return list(result.all())

    async def resolve_event_ids(
        self, theme_id: int, event_rows: list[dict[str, Any]]
    ) -> list[int]:
        keys: list[str] = []
        for row in event_rows:
            published_at = row.get("published_at")
            if isinstance(published_at, datetime):
                keys.append(build_event_key(str(row.get("title", "")), published_at))
        if not keys:
            return []
        result = await self.session.scalars(
            select(ThemeDriverEvent.id).where(
                ThemeDriverEvent.theme_id == theme_id,
                ThemeDriverEvent.event_key.in_(keys),
            )
        )
        return list(result.all())

    @staticmethod
    def _event_to_input(event: ThemeDriverEvent) -> EventInput:
        return EventInput(
            title=event.title,
            published_at=event.published_at,
            theme_id=event.theme_id,
            source=event.source,
            event_key=event.event_key,
            summary=event.summary,
        )

    async def _load_recent_same_theme(
        self, theme_id: int, before: datetime, *, exclude_id: int | None = None
    ) -> list[EventInput]:
        window_start = before - timedelta(days=REPLAY_WINDOW_DAYS)
        query = select(ThemeDriverEvent).where(
            ThemeDriverEvent.theme_id == theme_id,
            ThemeDriverEvent.published_at >= window_start,
            ThemeDriverEvent.published_at < before,
        )
        if exclude_id is not None:
            query = query.where(ThemeDriverEvent.id != exclude_id)
        result = await self.session.scalars(
            query.order_by(desc(ThemeDriverEvent.published_at))
        )
        return [self._event_to_input(event) for event in result.all()]

    async def _classify_one(self, event: ThemeDriverEvent) -> None:
        recent = await self._load_recent_same_theme(
            event.theme_id, event.published_at, exclude_id=event.id
        )
        result = classify_event(self._event_to_input(event), recent)
        await self.apply_classification(event.id, result, method="rules")

    async def classify_event_ids(self, event_ids: list[int]) -> int:
        if not event_ids:
            return 0
        result = await self.session.scalars(
            select(ThemeDriverEvent)
            .where(ThemeDriverEvent.id.in_(event_ids))
            .order_by(ThemeDriverEvent.published_at)
        )
        events = list(result.all())
        for event in events:
            await self._classify_one(event)
        return len(events)

    async def classify_recent(self, days: int = 7) -> int:
        since = datetime.now(UTC) - timedelta(days=days)
        result = await self.session.scalars(
            select(ThemeDriverEvent)
            .where(
                ThemeDriverEvent.published_at >= since,
                or_(
                    ThemeDriverEvent.freshness == "unknown",
                    ThemeDriverEvent.classified_by.is_(None),
                ),
            )
            .order_by(ThemeDriverEvent.published_at)
        )
        events = list(result.all())
        classified = 0
        for event in events:
            await self._classify_one(event)
            classified += 1
        return classified
