"""AKShare 股票数据爬虫

使用 AKShare Python 库获取股票基本信息。
"""

import asyncio
import logging
from decimal import Decimal
from typing import Any

import akshare as ak
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.stock import Stock
from app.scrapers.base import BaseScraper
from app.scrapers.anti_scraping import AntiScrapingMiddleware

logger = logging.getLogger(__name__)


class AKShareScraper(BaseScraper):
    """AKShare 股票数据爬虫

    使用 AKShare 库获取股票基本信息。
    """

    source_name = "akshare"

    def __init__(self, middleware: AntiScrapingMiddleware | None = None):
        """初始化爬虫

        Args:
            middleware: 反爬虫中间件实例（AKShare 不使用，但保持接口一致）
        """
        super().__init__(middleware)
        self._stock_data: list[dict[str, Any]] = []

    async def fetch_stock_info(self) -> list[dict[str, Any]]:
        """获取股票基本信息

        Returns:
            股票数据列表
        """
        logger.info(f"[{self.source_name}] 开始获取股票信息")

        try:
            # 使用 AKShare 获取 A 股股票列表
            # ak.stock_info_a_code_name() 返回股票代码和名称
            # 使用 asyncio.to_thread 避免阻塞事件循环
            stock_df = await asyncio.to_thread(ak.stock_info_a_code_name)

            if stock_df is None or stock_df.empty:
                logger.warning(f"[{self.source_name}] 未获取到股票数据")
                return []

            # 转换为字典列表
            stocks = []
            for _, row in stock_df.iterrows():
                try:
                    stock = {
                        "code": str(row.get("code", "")),
                        "name": str(row.get("name", "")),
                        "industry": "",
                        "market_cap": None,
                        "exchange": self._detect_exchange(str(row.get("code", ""))),
                    }

                    # 验证必填字段
                    if stock["code"] and stock["name"]:
                        stocks.append(stock)
                    else:
                        logger.warning(f"[{self.source_name}] 跳过无效股票数据: {row}")

                except Exception as e:
                    logger.warning(f"[{self.source_name}] 解析股票数据失败: {e}")
                    continue

            logger.info(f"[{self.source_name}] 获取到 {len(stocks)} 只股票")
            return stocks

        except Exception as e:
            logger.error(f"[{self.source_name}] 获取股票信息失败: {e}")
            raise

    def _detect_exchange(self, code: str) -> str:
        """根据股票代码检测交易所

        Args:
            code: 股票代码

        Returns:
            交易所代码 (SH/SZ/BJ)
        """
        if not code:
            return ""

        # 上海证券交易所：600xxx, 601xxx, 603xxx, 605xxx, 688xxx
        if code.startswith(("600", "601", "603", "605", "688")):
            return "SH"

        # 深圳证券交易所：000xxx, 001xxx, 002xxx, 003xxx, 300xxx
        if code.startswith(("000", "001", "002", "003", "300")):
            return "SZ"

        # 北京证券交易所：8xxxxx, 4xxxxx
        if code.startswith(("8", "4")):
            return "BJ"

        return ""

    def parse(self, html: str) -> list[dict[str, Any]]:
        """解析页面内容（实现 BaseScraper 抽象方法）

        Args:
            html: 页面 HTML（此处未使用）

        Returns:
            缓存的股票数据
        """
        # AKShare 直接返回数据，此方法仅为实现抽象接口
        return self._stock_data

    async def save(self, data: list[dict[str, Any]]) -> int:
        """保存股票数据（幂等更新）

        Args:
            data: 股票数据列表

        Returns:
            保存的记录数
        """
        saved_count = 0

        async with AsyncSessionLocal() as session:
            for stock_data in data:
                try:
                    # 查询现有记录（按 code 匹配）
                    existing = await session.execute(
                        select(Stock).where(Stock.code == stock_data["code"])
                    )
                    stock = existing.scalar_one_or_none()

                    if stock:
                        # 更新现有记录（AKShare 为权威来源）
                        stock.name = stock_data["name"]
                        if stock_data.get("industry"):
                            stock.industry = stock_data["industry"]
                        if stock_data.get("market_cap") is not None:
                            stock.market_cap = stock_data["market_cap"]
                        if stock_data.get("exchange"):
                            stock.exchange = stock_data["exchange"]
                        logger.debug(
                            f"[{self.source_name}] 更新股票: {stock_data['code']} {stock_data['name']}"
                        )
                    else:
                        # 创建新记录
                        stock = Stock(
                            code=stock_data["code"],
                            name=stock_data["name"],
                            industry=stock_data.get("industry"),
                            market_cap=stock_data.get("market_cap"),
                            exchange=stock_data.get("exchange"),
                        )
                        session.add(stock)
                        logger.debug(
                            f"[{self.source_name}] 创建股票: {stock_data['code']} {stock_data['name']}"
                        )

                    saved_count += 1

                except Exception as e:
                    logger.error(
                        f"[{self.source_name}] 保存股票失败: {e}, "
                        f"数据: {stock_data}"
                    )
                    continue

            await session.commit()

        logger.info(f"[{self.source_name}] 保存了 {saved_count} 只股票")
        return saved_count

    async def run(
        self, url: str = "", params: dict[str, Any] | None = None
    ) -> tuple[list[dict[str, Any]], int]:
        """执行完整爬虫生命周期

        Args:
            url: 未使用（AKShare 不需要 URL）
            params: 额外参数（可选）

        Returns:
            (股票数据列表, 保存的记录数) 元组
        """
        logger.info(f"[{self.source_name}] 开始爬取股票数据")

        try:
            # Step 1: 获取股票信息
            stocks = await self.fetch_stock_info()
            logger.info(f"[{self.source_name}] 获取到 {len(stocks)} 只股票")

            if not stocks:
                logger.warning(f"[{self.source_name}] 未获取到股票数据")
                return [], 0

            # 缓存数据供 parse 方法使用
            self._stock_data = stocks

            # Step 2: 保存股票数据
            saved_count = await self.save(stocks)

            logger.info(
                f"[{self.source_name}] 爬取任务完成: 保存 {saved_count} 只股票"
            )

            return stocks, saved_count

        except Exception as e:
            logger.error(f"[{self.source_name}] 爬取股票数据失败: {e}")
            raise

    async def close(self) -> None:
        """关闭爬虫资源"""
        await self.middleware.close()
