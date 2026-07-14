"""爬虫调度器

管理爬虫执行：触发运行、状态追踪、错误记录。
"""

import asyncio
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.repositories.scraper_run import ScraperRunRepository
from app.scrapers.registry import ScraperRegistry, scraper_registry
from app.scrapers.anti_scraping import AntiScrapingMiddleware
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ScraperScheduler:
    """爬虫调度器

    管理爬虫的执行和状态追踪。
    """

    def __init__(self, registry: ScraperRegistry | None = None):
        self.registry = registry or scraper_registry

    async def run(self, source: str, params: dict | None = None) -> int:
        """触发爬虫运行

        在后台异步执行爬虫，立即返回 run_id。

        Args:
            source: 数据源名称
            params: 爬虫参数

        Returns:
            运行记录 ID

        Raises:
            ValueError: 如果数据源未注册
        """
        scraper_cls = self.registry.get(source)
        if scraper_cls is None:
            raise ValueError(f"未注册的数据源: {source}")

        # 创建运行记录
        async with AsyncSessionLocal() as session:
            repo = ScraperRunRepository(session)
            run = await repo.create(source)
            await session.commit()
            run_id = run.id

        # 后台执行爬虫，添加异常回调避免静默吞没错误
        task = asyncio.create_task(self._execute_scraper(source, run_id, params))
        task.add_done_callback(
            lambda t: t.exception() and logger.error(
                f"爬虫 {source} 后台任务异常: {t.exception()}"
            )
        )

        return run_id

    async def _execute_scraper(
        self, source: str, run_id: int, params: dict | None = None
    ) -> None:
        """执行爬虫（后台任务）

        Args:
            source: 数据源名称
            run_id: 运行记录 ID
            params: 爬虫参数
        """
        settings = get_settings()
        proxy_url = getattr(settings, "PROXY_URL", None)
        proxy_enabled = getattr(settings, "PROXY_ENABLED", False)

        middleware = AntiScrapingMiddleware(
            proxy_url=proxy_url if proxy_enabled else None,
        )

        scraper_cls = self.registry.get(source)
        if scraper_cls is None:
            logger.error(f"数据源 {source} 未注册")
            return

        scraper = scraper_cls(middleware=middleware)
        items_scraped = 0
        error_message = None

        try:
            # URL 从 params 中提取，不强制要求（部分爬虫如 eastmoney 内置 URL）
            url = (params or {}).pop("url", "")
            data, items_scraped = await scraper.run(url, params)
            status = "completed"
            logger.info(f"爬虫 {source} 完成，共 {items_scraped} 条数据")

        except Exception as e:
            status = "failed"
            error_message = str(e)
            logger.error(f"爬虫 {source} 失败: {e}")

        finally:
            await scraper.close()

        # 更新运行记录
        try:
            async with AsyncSessionLocal() as session:
                repo = ScraperRunRepository(session)
                await repo.update_status(
                    run_id=run_id,
                    status=status,
                    items_scraped=items_scraped,
                    error_message=error_message,
                )
                await session.commit()
        except Exception as e:
            logger.error(f"更新运行记录失败: {e}")


# 全局调度器实例
scraper_scheduler = ScraperScheduler()
