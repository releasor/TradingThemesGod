"""题材研究信息的有界周期刷新任务。"""

import asyncio
from contextlib import suppress
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.models.theme import Theme
from app.models.theme_driver_event import ThemeDriverEvent
from app.models.theme_profile import ThemeProfile
from app.services.theme_insight import ThemeInsightRefreshService

logger = get_logger(__name__)


class ThemeInsightScheduler:
    def __init__(self, batch_size: int = 10, profile_max_age_days: int = 7):
        self.batch_size = batch_size
        self.profile_max_age_days = profile_max_age_days
        self._task: asyncio.Task[None] | None = None

    def start(self, interval_seconds: int) -> asyncio.Task[None]:
        if interval_seconds <= 0:
            raise ValueError("题材研究更新间隔必须大于 0 秒")
        if self._task is not None and not self._task.done():
            return self._task
        self._task = asyncio.create_task(self._loop(interval_seconds))
        return self._task

    async def stop(self) -> None:
        task, self._task = self._task, None
        if task is None:
            return
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

    async def _loop(self, interval_seconds: int) -> None:
        while True:
            try:
                await self.run_batch()
            except Exception as exc:
                logger.warning("theme_insight_periodic_batch_failed", error=str(exc))
            await asyncio.sleep(interval_seconds)

    async def run_batch(self) -> int:
        last_event_crawled_at = (
            select(func.max(ThemeDriverEvent.crawled_at))
            .where(ThemeDriverEvent.theme_id == Theme.id)
            .correlate(Theme)
            .scalar_subquery()
        )
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(
                    Theme.id,
                    ThemeProfile.generated_at,
                    last_event_crawled_at.label("last_event_crawled_at"),
                    Theme.insights_last_attempted_at,
                )
                .outerjoin(ThemeProfile, ThemeProfile.theme_id == Theme.id)
                .where(Theme.deleted_at.is_(None))
            )
            rows = list(result.all())
        now = datetime.now(UTC)
        oldest = datetime.min.replace(tzinfo=UTC)

        def normalize(value: datetime | None) -> datetime | None:
            if value is None:
                return None
            return value if value.tzinfo is not None else value.replace(tzinfo=UTC)

        rows.sort(
            key=lambda row: (
                normalize(row[3]) or normalize(row[2]) or oldest,
                row[0],
            )
        )
        candidates = rows[: self.batch_size]
        completed = 0
        profile_cutoff = now - timedelta(days=self.profile_max_age_days)
        for (
            theme_id,
            profile_generated_at,
            _last_event_at,
            _last_attempted_at,
        ) in candidates:
            async with AsyncSessionLocal() as session:
                service = ThemeInsightRefreshService(session)
                try:
                    generated_at = normalize(profile_generated_at)
                    refresh_profile = (
                        generated_at is None or generated_at < profile_cutoff
                    )
                    await service.refresh(theme_id, refresh_profile=refresh_profile)
                    completed += 1
                except Exception as exc:
                    await session.rollback()
                    logger.warning(
                        "theme_insight_periodic_failed",
                        theme_id=theme_id,
                        error=str(exc),
                    )
                finally:
                    try:
                        await service.insights.mark_refresh_attempt(theme_id, now)
                        await session.commit()
                    finally:
                        await service.research.middleware.close()
        return completed


theme_insight_scheduler = ThemeInsightScheduler()
