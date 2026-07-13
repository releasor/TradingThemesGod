"""爬虫基类

提供爬虫生命周期管理：fetch → parse → save。
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from app.scrapers.anti_scraping import AntiScrapingMiddleware

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """爬虫基类

    子类需要实现 parse() 和 save() 方法。
    run() 方法自动编排 fetch → parse → save 生命周期。
    """

    # 数据源名称，子类必须定义
    source_name: str = ""

    def __init__(self, middleware: AntiScrapingMiddleware | None = None):
        """初始化爬虫

        Args:
            middleware: 反爬虫中间件实例。如果不提供，将创建默认实例。
        """
        self.middleware = middleware or AntiScrapingMiddleware()

    async def fetch(self, url: str, params: dict[str, Any] | None = None) -> str:
        """获取页面内容

        Args:
            url: 请求 URL
            params: 请求参数

        Returns:
            页面 HTML 内容
        """
        logger.info(f"[{self.source_name}] 正在抓取: {url}")
        response = await self.middleware.get(url, params=params)
        response.raise_for_status()
        return response.text

    @abstractmethod
    def parse(self, html: str) -> list[dict[str, Any]]:
        """解析页面内容

        Args:
            html: 页面 HTML

        Returns:
            解析后的数据列表
        """
        ...

    @abstractmethod
    async def save(self, data: list[dict[str, Any]]) -> int:
        """保存数据

        Args:
            data: 要保存的数据列表

        Returns:
            保存的记录数
        """
        ...

    async def run(
        self, url: str, params: dict[str, Any] | None = None
    ) -> tuple[list[dict[str, Any]], int]:
        """执行完整爬虫生命周期

        Args:
            url: 目标 URL
            params: 请求参数

        Returns:
            (parsed_data, saved_count) 元组
        """
        logger.info(f"[{self.source_name}] 开始爬取任务")

        # Step 1: Fetch
        html = await self.fetch(url, params)
        logger.info(f"[{self.source_name}] 获取到 {len(html)} 字节")

        # Step 2: Parse
        data = self.parse(html)
        logger.info(f"[{self.source_name}] 解析到 {len(data)} 条数据")

        # Step 3: Save
        saved_count = await self.save(data)
        logger.info(f"[{self.source_name}] 保存了 {saved_count} 条数据")

        logger.info(f"[{self.source_name}] 爬取任务完成")
        return data, saved_count

    async def close(self) -> None:
        """关闭爬虫资源"""
        await self.middleware.close()
