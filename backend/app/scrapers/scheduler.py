"""爬虫调度器

管理爬虫执行：触发运行、状态追踪、错误记录。
"""

import asyncio
from contextlib import suppress

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.repositories.scraper_run import ScraperRunRepository
from app.scrapers.anti_scraping import AntiScrapingMiddleware
from app.scrapers.registry import ScraperRegistry, scraper_registry

logger = get_logger(__name__)


class ScraperScheduler:
    """爬虫调度器

    管理爬虫的执行和状态追踪。
    """

    def __init__(self, registry: ScraperRegistry | None = None):
        self.registry = registry or scraper_registry
        self._execution_tasks: dict[str, asyncio.Task[None]] = {}
        self._periodic_tasks: dict[str, asyncio.Task[None]] = {}
        self._running_run_ids: dict[str, int] = {}
        # 轻量行情刷新锁：与全量采集互不阻塞
        self.quotes_refresh_lock = asyncio.Lock()

    def is_running(self, source: str) -> bool:
        """判断指定数据源是否正在采集"""
        task = self._execution_tasks.get(source)
        return task is not None and not task.done()

    def is_quotes_refresh_running(self) -> bool:
        """是否有轻量行情刷新正在进行"""
        return self.quotes_refresh_lock.locked()

    def get_running_run_id(self, source: str) -> int | None:
        """返回当前进行中的 run_id（若有）。"""
        if not self.is_running(source):
            return None
        return self._running_run_ids.get(source)

    def start_periodic(
        self,
        source: str,
        interval_seconds: int,
    ) -> asyncio.Task[None]:
        """启动指定数据源的周期采集任务"""
        if self.registry.get(source) is None:
            raise ValueError(f"未注册的数据源: {source}")
        if interval_seconds <= 0:
            raise ValueError("采集间隔必须大于 0 秒")

        existing_task = self._periodic_tasks.get(source)
        if existing_task is not None and not existing_task.done():
            return existing_task

        task = asyncio.create_task(
            self._periodic_loop(source, interval_seconds),
            name=f"scraper-periodic-{source}",
        )
        self._periodic_tasks[source] = task
        return task

    async def stop_periodic(self, source: str) -> None:
        """停止指定数据源的周期采集任务"""
        task = self._periodic_tasks.pop(source, None)
        if task is None:
            return

        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

    async def _periodic_loop(self, source: str, interval_seconds: int) -> None:
        """立即执行采集，并按固定间隔持续触发"""
        while True:
            if self.is_running(source):
                logger.warning(f"爬虫 {source} 仍在运行，跳过本次周期采集")
            else:
                try:
                    await self.run(source)
                except Exception as exc:
                    logger.error(f"启动爬虫 {source} 周期采集失败: {exc}")

            await asyncio.sleep(interval_seconds)

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

        # 已在运行：返回现有 run_id，让前端附着轮询，避免「切源成功」但原任务仍阻塞轻量刷新
        if self.is_running(source):
            existing_run_id = self._running_run_ids.get(source)
            if existing_run_id is not None:
                logger.info(
                    f"爬虫 {source} 已在运行，复用 run_id={existing_run_id}"
                )
                return existing_run_id
            raise ValueError(f"爬虫 {source} 正在运行中，请稍后再试")

        # 创建运行记录
        async with AsyncSessionLocal() as session:
            repo = ScraperRunRepository(session)
            run = await repo.create(source)
            await session.commit()
            run_id = run.id

        # 后台执行爬虫，添加异常回调避免静默吞没错误
        task = asyncio.create_task(
            self._execute_scraper(source, run_id, dict(params or {})),
            name=f"scraper-execution-{source}-{run_id}",
        )
        self._execution_tasks[source] = task
        self._running_run_ids[source] = run_id
        task.add_done_callback(
            lambda completed_task: self._handle_execution_done(
                source,
                completed_task,
            )
        )

        return run_id

    def _handle_execution_done(
        self,
        source: str,
        task: asyncio.Task[None],
    ) -> None:
        """清理已结束任务并记录未处理异常"""
        if self._execution_tasks.get(source) is task:
            self._execution_tasks.pop(source, None)
            self._running_run_ids.pop(source, None)

        if task.cancelled():
            return

        exception = task.exception()
        if exception is not None:
            logger.error(f"爬虫 {source} 后台任务异常: {exception}")

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
            run_params = dict(params or {})
            url = run_params.pop("url", "")
            data, items_scraped = await scraper.run(url, run_params)
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
