"""爬虫运行记录仓储

提供 ScraperRun 的数据库操作。
"""

from datetime import datetime, timezone
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.scraper_run import ScraperRun


class ScraperRunRepository:
    """爬虫运行记录仓储"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, source: str) -> ScraperRun:
        """创建运行记录"""
        run = ScraperRun(
            source=source,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        self.session.add(run)
        await self.session.flush()
        return run

    async def get(self, run_id: int) -> ScraperRun | None:
        """获取运行记录"""
        result = await self.session.execute(
            select(ScraperRun).where(ScraperRun.id == run_id)
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        run_id: int,
        status: str,
        items_scraped: int = 0,
        error_message: str | None = None,
    ) -> ScraperRun | None:
        """更新运行状态"""
        run = await self.get(run_id)
        if run is None:
            return None
        run.status = status
        run.items_scraped = items_scraped
        run.error_message = error_message
        if status in ("completed", "failed"):
            run.finished_at = datetime.now(timezone.utc)
        await self.session.flush()
        return run

    async def list_by_source(
        self, source: str | None = None, limit: int = 20
    ) -> list[ScraperRun]:
        """按数据源列出运行记录"""
        stmt = select(ScraperRun).order_by(desc(ScraperRun.started_at))
        if source:
            stmt = stmt.where(ScraperRun.source == source)
        stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
