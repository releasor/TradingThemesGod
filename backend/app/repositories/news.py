"""新闻文章仓储。"""

from datetime import datetime
from hashlib import sha256
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.news_article import NewsArticle
from app.repositories.base import BaseRepository


class NewsRepository(BaseRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def list_latest(
        self,
        limit: int = 50,
        source: str | None = None,
        category: str | None = None,
        sources: set[str] | None = None,
        offset: int = 0,
    ) -> tuple[list[NewsArticle], int]:
        query = select(NewsArticle)
        if source:
            query = query.where(NewsArticle.source == source)
        if sources is not None:
            query = query.where(NewsArticle.source.in_(sources))
        if category:
            query = query.where(NewsArticle.category == category)
        count = await self.session.scalar(
            select(func.count()).select_from(query.subquery())
        )
        result = await self.session.execute(
            query.order_by(NewsArticle.published_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), count or 0

    async def upsert_many(self, items: list[dict[str, Any]]) -> int:
        if not items:
            return 0
        rows = []
        for item in items:
            row = dict(item)
            row["url_hash"] = sha256(row["url"].encode("utf-8")).hexdigest()
            rows.append(row)

        hashes = [row["url_hash"] for row in rows]
        existing = await self.session.scalars(
            select(NewsArticle.url_hash).where(NewsArticle.url_hash.in_(hashes))
        )
        existing_hashes = set(existing.all())
        statement = insert(NewsArticle).values(rows)
        statement = statement.on_duplicate_key_update(
            title=statement.inserted.title,
            summary=statement.inserted.summary,
            category=statement.inserted.category,
            published_at=statement.inserted.published_at,
            crawled_at=statement.inserted.crawled_at,
            source_heat=statement.inserted.source_heat,
            heat_score=statement.inserted.heat_score,
        )
        await self.session.execute(statement)
        await self.session.commit()
        return len(set(hashes) - existing_hashes)

    async def list_theme_candidates(
        self, keywords: list[str], since: datetime, limit: int = 50
    ) -> list[NewsArticle]:
        cleaned = [keyword.strip() for keyword in keywords if keyword.strip()]
        if not cleaned:
            return []
        conditions = []
        for keyword in cleaned:
            escaped = (
                keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            )
            pattern = f"%{escaped}%"
            conditions.extend(
                (
                    NewsArticle.title.like(pattern, escape="\\"),
                    NewsArticle.summary.like(pattern, escape="\\"),
                )
            )
        result = await self.session.execute(
            select(NewsArticle)
            .where(NewsArticle.published_at >= since, or_(*conditions))
            .order_by(NewsArticle.published_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
