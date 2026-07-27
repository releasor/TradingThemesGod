"""爬虫运行记录仓储

提供 ScraperRun 的数据库操作。
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scraper_run import ScraperRun
from app.repositories.base import BaseRepository


class ScraperRunRepository(BaseRepository):
    """爬虫运行记录仓储"""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

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
        self,
        source: str | None = None,
        limit: int = 20,
        *,
        status: str | None = None,
    ) -> list[ScraperRun]:
        """按数据源列出运行记录"""
        stmt = select(ScraperRun).order_by(desc(ScraperRun.started_at))
        if source:
            stmt = stmt.where(ScraperRun.source == source)
        if status:
            stmt = stmt.where(ScraperRun.status == status)
        stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def fail_stale_running(self, *, older_than_hours: float = 2) -> int:
        """将长时间未结束的 running 记录标记为失败，避免僵尸任务干扰。"""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
        result = await self.session.execute(
            update(ScraperRun)
            .where(
                ScraperRun.status == "running",
                ScraperRun.finished_at.is_(None),
                ScraperRun.started_at < cutoff,
            )
            .values(
                status="failed",
                finished_at=datetime.now(timezone.utc),
                error_message="进程中断后的僵尸任务，已自动清理",
            )
        )
        await self.session.flush()
        return int(result.rowcount or 0)

    async def fail_all_running(self, *, reason: str = "采集已中断并清理") -> int:
        """将全部 running 记录标记为失败（用于进程重启后清理）。"""
        result = await self.session.execute(
            update(ScraperRun)
            .where(
                ScraperRun.status == "running",
                ScraperRun.finished_at.is_(None),
            )
            .values(
                status="failed",
                finished_at=datetime.now(timezone.utc),
                error_message=reason,
            )
        )
        await self.session.flush()
        return int(result.rowcount or 0)
