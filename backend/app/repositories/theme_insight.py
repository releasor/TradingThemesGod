"""题材档案、驱动事件和市场快照的数据访问。"""

from datetime import date, datetime, timedelta
from hashlib import sha256
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import desc, func, select, update
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.theme_insights import MarketCounts, build_event_key
from app.models.theme import Theme
from app.models.theme_driver_event import ThemeDriverEvent
from app.models.theme_market_snapshot import ThemeMarketSnapshot
from app.models.theme_profile import ThemeProfile
from app.repositories.base import BaseRepository
from app.schemas.theme_insight import ExtractedThemeProfile

TRACKING_QUERY_KEYS = {"from", "ref", "source", "spm", "track"}


def canonicalize_url(url: str) -> str:
    """规范 URL，用于过滤追踪参数并稳定计算增量去重哈希。"""
    parsed = urlsplit(url.strip())
    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower()
    port = parsed.port
    is_default_port = (scheme == "https" and port == 443) or (
        scheme == "http" and port == 80
    )
    netloc = hostname if port is None or is_default_port else f"{hostname}:{port}"
    query_items = sorted(
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_QUERY_KEYS
    )
    return urlunsplit((scheme, netloc, parsed.path or "/", urlencode(query_items), ""))


class ThemeInsightRepository(BaseRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_profile(self, theme_id: int) -> ThemeProfile | None:
        return await self.session.scalar(
            select(ThemeProfile).where(ThemeProfile.theme_id == theme_id)
        )

    async def upsert_profile(
        self,
        theme_id: int,
        payload: ExtractedThemeProfile,
        sources: list[dict[str, Any]],
        generated_at: datetime,
    ) -> ThemeProfile:
        profile = await self.get_profile(theme_id)
        if profile is None:
            profile = ThemeProfile(theme_id=theme_id)
        profile.definition = payload.definition
        profile.core_logic = payload.core_logic
        profile.applications = payload.applications
        profile.catalysts = payload.catalysts
        profile.risks = payload.risks
        profile.sources = sources
        profile.generated_at = generated_at
        self.session.add(profile)
        await self.session.flush()
        return profile

    async def list_recent_events(
        self, theme_id: int, now: datetime, limit: int = 5
    ) -> list[ThemeDriverEvent]:
        async def query(days: int) -> list[ThemeDriverEvent]:
            result = await self.session.execute(
                select(ThemeDriverEvent)
                .where(
                    ThemeDriverEvent.theme_id == theme_id,
                    ThemeDriverEvent.published_at >= now - timedelta(days=days),
                )
                .order_by(
                    desc(ThemeDriverEvent.published_at),
                    desc(ThemeDriverEvent.relevance_score),
                )
                .limit(limit)
            )
            return list(result.scalars().all())

        items = await query(7)
        return items if len(items) >= limit else await query(30)

    async def upsert_events(
        self, theme_id: int, events: list[dict[str, Any]]
    ) -> tuple[int, int]:
        if not events:
            return 0, 0
        rows = []
        for event in events:
            row = dict(event)
            row["theme_id"] = theme_id
            row["url"] = canonicalize_url(row["url"])
            row["url_hash"] = sha256(row["url"].encode("utf-8")).hexdigest()
            row["event_key"] = build_event_key(row["title"], row["published_at"])
            rows.append(row)
        event_keys = [row["event_key"] for row in rows]
        existing = set(
            (
                await self.session.scalars(
                    select(ThemeDriverEvent.event_key).where(
                        ThemeDriverEvent.theme_id == theme_id,
                        ThemeDriverEvent.event_key.in_(event_keys),
                    )
                )
            ).all()
        )
        statement = insert(ThemeDriverEvent).values(rows)
        statement = statement.on_duplicate_key_update(
            title=statement.inserted.title,
            summary=statement.inserted.summary,
            source=statement.inserted.source,
            url=statement.inserted.url,
            url_hash=statement.inserted.url_hash,
            event_key=statement.inserted.event_key,
            published_at=statement.inserted.published_at,
            relevance_score=statement.inserted.relevance_score,
            crawled_at=statement.inserted.crawled_at,
            updated_at=func.now(),
        )
        await self.session.execute(statement)
        return len(set(event_keys) - existing), len(set(event_keys) & existing)

    async def mark_refresh_attempt(self, theme_id: int, attempted_at: datetime) -> None:
        await self.session.execute(
            update(Theme)
            .where(Theme.id == theme_id)
            .values(insights_last_attempted_at=attempted_at)
        )

    async def get_latest_snapshot(self, theme_id: int) -> ThemeMarketSnapshot | None:
        return await self.session.scalar(
            select(ThemeMarketSnapshot)
            .where(ThemeMarketSnapshot.theme_id == theme_id)
            .order_by(desc(ThemeMarketSnapshot.trade_date))
            .limit(1)
        )

    async def upsert_snapshot(
        self,
        theme_id: int,
        trade_date: date,
        counts: MarketCounts,
        calculated_at: datetime,
    ) -> ThemeMarketSnapshot:
        snapshot = await self.session.scalar(
            select(ThemeMarketSnapshot).where(
                ThemeMarketSnapshot.theme_id == theme_id,
                ThemeMarketSnapshot.trade_date == trade_date,
            )
        )
        if snapshot is None:
            snapshot = ThemeMarketSnapshot(theme_id=theme_id, trade_date=trade_date)
        for field in (
            "up_count",
            "down_count",
            "flat_count",
            "suspended_count",
        ):
            setattr(snapshot, field, getattr(counts, field))
        if counts.limit_up_count is not None:
            snapshot.limit_up_count = counts.limit_up_count
        if counts.limit_down_count is not None:
            snapshot.limit_down_count = counts.limit_down_count
        snapshot.calculated_at = calculated_at
        self.session.add(snapshot)
        await self.session.flush()
        return snapshot
