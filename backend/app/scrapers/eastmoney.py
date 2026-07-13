"""东方财富题材爬虫

从东方财富 API 获取题材概念列表和关联股票数据。
"""

import logging
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.theme import Theme
from app.models.theme_stock import ThemeStock
from app.models.stock import Stock
from app.scrapers.base import BaseScraper
from app.scrapers.anti_scraping import AntiScrapingMiddleware

logger = logging.getLogger(__name__)

# 东方财富 API 基础配置
EASTMONEY_API_BASE = "http://push2.eastmoney.com/api/qt/clist/get"

# 默认请求参数
DEFAULT_PARAMS = {
    "fid": "f3",
    "po": "1",
    "pz": "500",  # 每页数量
    "np": "1",
    "fltt": "2",
    "invt": "2",
    "ut": "bd1d9ddb04089700cf9c27f6f7426281",
}

# 题材板块前缀
THEME_BOARD_PREFIX = "BK"

# 题材分类关键词映射（模块级常量，避免每次调用重建）
THEME_CATEGORIES = {
    "新能源": ["锂电", "光伏", "风电", "储能", "新能源", "电池"],
    "科技": ["芯片", "半导体", "人工智能", "AI", "5G", "通信", "科技"],
    "医药": ["医药", "医疗", "生物", "疫苗", "健康"],
    "消费": ["白酒", "食品", "消费", "零售", "电商"],
    "金融": ["银行", "证券", "保险", "金融"],
    "制造": ["机械", "制造", "工业", "自动化"],
    "地产": ["地产", "房地产", "物业"],
    "军工": ["军工", "国防", "航天"],
}


class EastMoneyScraper(BaseScraper):
    """东方财富题材爬虫

    从东方财富 API 获取题材概念列表和关联股票数据。
    """

    source_name = "eastmoney"

    def __init__(self, middleware: AntiScrapingMiddleware | None = None):
        """初始化爬虫

        Args:
            middleware: 反爬虫中间件实例
        """
        super().__init__(middleware)

    async def fetch_json(self, url: str, params: dict[str, Any] | None = None) -> dict:
        """获取 JSON API 数据

        Args:
            url: API URL
            params: 请求参数

        Returns:
            解析后的 JSON 数据
        """
        logger.info(f"[{self.source_name}] 正在请求 API: {url}")
        response = await self.middleware.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def parse_theme_list(self, data: dict) -> list[dict[str, Any]]:
        """解析题材列表数据

        Args:
            data: API 返回的 JSON 数据

        Returns:
            题材数据列表
        """
        themes = []
        diff = data.get("data", {}).get("diff", [])

        if not diff:
            logger.warning(f"[{self.source_name}] 未获取到题材数据")
            return themes

        for item in diff:
            try:
                # 提取题材代码
                code = str(item.get("f12", ""))
                if not code.startswith(THEME_BOARD_PREFIX):
                    code = f"{THEME_BOARD_PREFIX}{code}"

                # 构建题材数据
                theme = {
                    "name": item.get("f14", ""),  # 题材名称
                    "code": code,  # 题材代码
                    "heat_index": Decimal(str(item.get("f8", 0))),  # 热度指数
                    "rise_fall_pct": Decimal(str(item.get("f3", 0))),  # 涨跌幅
                    "stock_count": int(item.get("f104", 0)),  # 关联股票数量
                    "category": self._extract_category(item.get("f14", "")),  # 分类
                    "source": self.source_name,
                }

                # 验证必填字段
                if theme["name"] and theme["code"]:
                    themes.append(theme)
                else:
                    logger.warning(f"[{self.source_name}] 跳过无效题材数据: {item}")

            except (ValueError, TypeError) as e:
                logger.warning(f"[{self.source_name}] 解析题材数据失败: {e}, 数据: {item}")
                continue

        logger.info(f"[{self.source_name}] 解析到 {len(themes)} 个题材")
        return themes

    def parse_theme_stocks(self, data: dict, theme_code: str) -> list[dict[str, Any]]:
        """解析题材关联股票数据

        Args:
            data: API 返回的 JSON 数据
            theme_code: 题材代码

        Returns:
            股票数据列表
        """
        stocks = []
        diff = data.get("data", {}).get("diff", [])

        if not diff:
            logger.info(f"[{self.source_name}] 题材 {theme_code} 无关联股票")
            return stocks

        for item in diff:
            try:
                stock = {
                    "code": str(item.get("f12", "")),  # 股票代码
                    "name": item.get("f14", ""),  # 股票名称
                    "rise_fall_pct": Decimal(str(item.get("f3", 0))),  # 涨跌幅
                    "current_price": Decimal(str(item.get("f2", 0))),  # 当前价格
                }

                # 验证必填字段
                if stock["code"] and stock["name"]:
                    stocks.append(stock)
                else:
                    logger.warning(f"[{self.source_name}] 跳过无效股票数据: {item}")

            except (ValueError, TypeError) as e:
                logger.warning(f"[{self.source_name}] 解析股票数据失败: {e}, 数据: {item}")
                continue

        logger.info(f"[{self.source_name}] 题材 {theme_code} 解析到 {len(stocks)} 只股票")
        return stocks

    def _extract_category(self, name: str) -> str:
        """从题材名称提取分类

        Args:
            name: 题材名称

        Returns:
            分类名称
        """
        name_lower = name.lower()
        for category, keywords in THEME_CATEGORIES.items():
            for keyword in keywords:
                if keyword.lower() in name_lower:
                    return category

        return "其他"

    def parse(self, html: str) -> list[dict[str, Any]]:
        """解析页面内容（实现 BaseScraper 抽象方法）

        Args:
            html: 页面 HTML（此处未使用，实际数据来自 JSON API）

        Returns:
            空列表（实际解析在 parse_theme_list 中完成）
        """
        # 东方财富使用 JSON API，此方法仅为实现抽象接口
        return []

    async def save(self, data: list[dict[str, Any]]) -> int:
        """保存数据（实现 BaseScraper 抽象方法）

        Args:
            data: 要保存的数据列表（此处未使用）

        Returns:
            保存的记录数
        """
        # 实际保存在 run() 方法中完成
        return 0

    async def _save_themes(self, themes: list[dict[str, Any]]) -> int:
        """幂等保存题材数据（批量查询优化）

        Args:
            themes: 题材数据列表

        Returns:
            保存的记录数
        """
        saved_count = 0

        async with AsyncSessionLocal() as session:
            # 批量查询现有题材（避免 N+1 查询）
            theme_names = [t["name"] for t in themes if t.get("name")]
            existing_result = await session.execute(
                select(Theme).where(
                    Theme.name.in_(theme_names),
                    Theme.deleted_at.is_(None),
                )
            )
            existing_map = {t.name: t for t in existing_result.scalars().all()}

            for theme_data in themes:
                try:
                    theme = existing_map.get(theme_data["name"])

                    if theme:
                        # 更新现有题材
                        theme.code = theme_data["code"]
                        theme.heat_index = theme_data["heat_index"]
                        theme.rise_fall_pct = theme_data["rise_fall_pct"]
                        theme.stock_count = theme_data["stock_count"]
                        theme.category = theme_data["category"]
                        theme.source = theme_data["source"]
                        logger.debug(f"[{self.source_name}] 更新题材: {theme_data['name']}")
                    else:
                        # 创建新题材
                        theme = Theme(
                            name=theme_data["name"],
                            code=theme_data["code"],
                            heat_index=theme_data["heat_index"],
                            rise_fall_pct=theme_data["rise_fall_pct"],
                            stock_count=theme_data["stock_count"],
                            category=theme_data["category"],
                            source=theme_data["source"],
                        )
                        session.add(theme)
                        logger.debug(f"[{self.source_name}] 创建题材: {theme_data['name']}")

                    saved_count += 1

                except Exception as e:
                    logger.error(f"[{self.source_name}] 保存题材失败: {e}, 数据: {theme_data}")
                    continue

            await session.commit()

        logger.info(f"[{self.source_name}] 保存了 {saved_count} 个题材")
        return saved_count

    async def _save_theme_stocks(
        self, theme_code: str, stocks: list[dict[str, Any]]
    ) -> int:
        """保存题材关联股票（批量查询优化）

        Args:
            theme_code: 题材代码
            stocks: 股票数据列表

        Returns:
            保存的记录数
        """
        saved_count = 0

        async with AsyncSessionLocal() as session:
            # 获取题材
            theme_result = await session.execute(
                select(Theme).where(Theme.code == theme_code, Theme.deleted_at.is_(None))
            )
            theme = theme_result.scalar_one_or_none()

            if not theme:
                logger.warning(f"[{self.source_name}] 未找到题材: {theme_code}")
                return 0

            # 批量查询现有股票（避免 N+1 查询）
            stock_codes = [s["code"] for s in stocks if s.get("code")]
            existing_stocks_result = await session.execute(
                select(Stock).where(Stock.code.in_(stock_codes))
            )
            stock_map = {s.code: s for s in existing_stocks_result.scalars().all()}

            # 批量查询现有关联关系
            existing_stock_ids = list(stock_map.values())
            if existing_stock_ids:
                theme_stock_result = await session.execute(
                    select(ThemeStock).where(
                        ThemeStock.theme_id == theme.id,
                        ThemeStock.stock_id.in_([s.id for s in existing_stock_ids]),
                    )
                )
                theme_stock_map = {ts.stock_id: ts for ts in theme_stock_result.scalars().all()}
            else:
                theme_stock_map = {}

            for stock_data in stocks:
                try:
                    stock = stock_map.get(stock_data["code"])

                    if not stock:
                        # 创建新股票
                        stock = Stock(
                            code=stock_data["code"],
                            name=stock_data["name"],
                            current_price=stock_data.get("current_price"),
                            rise_fall_pct=stock_data.get("rise_fall_pct"),
                        )
                        session.add(stock)
                        await session.flush()  # 获取 stock.id
                        stock_map[stock_data["code"]] = stock

                    # 创建或更新关联关系
                    theme_stock = theme_stock_map.get(stock.id)

                    if not theme_stock:
                        theme_stock = ThemeStock(
                            theme_id=theme.id,
                            stock_id=stock.id,
                            sort_order=saved_count,
                        )
                        session.add(theme_stock)

                    saved_count += 1

                except Exception as e:
                    logger.error(
                        f"[{self.source_name}] 保存题材股票关联失败: {e}, "
                        f"题材: {theme_code}, 股票: {stock_data}"
                    )
                    continue

            await session.commit()

        logger.info(f"[{self.source_name}] 题材 {theme_code} 保存了 {saved_count} 只股票")
        return saved_count

    async def run(
        self, url: str = "", params: dict[str, Any] | None = None
    ) -> tuple[list[dict[str, Any]], int]:
        """执行完整爬虫生命周期

        Args:
            url: 未使用（使用默认 API）
            params: 额外参数

        Returns:
            (题材数据列表, 保存的记录数) 元组
        """
        logger.info(f"[{self.source_name}] 开始爬取任务")

        # Step 1: 获取题材列表
        theme_params = {**DEFAULT_PARAMS, "fs": f"b:{THEME_BOARD_PREFIX}"}
        if params:
            theme_params.update(params)

        try:
            theme_data = await self.fetch_json(EASTMONEY_API_BASE, theme_params)
        except Exception as e:
            logger.error(f"[{self.source_name}] 获取题材列表失败: {e}")
            raise

        # Step 2: 解析题材列表
        themes = self.parse_theme_list(theme_data)
        logger.info(f"[{self.source_name}] 解析到 {len(themes)} 个题材")

        if not themes:
            logger.warning(f"[{self.source_name}] 未获取到题材数据")
            return [], 0

        # Step 3: 保存题材
        saved_themes = await self._save_themes(themes)

        # Step 4: 获取并保存每个题材的关联股票
        total_stocks = 0
        for theme in themes:
            try:
                # 构建题材股票请求参数
                stock_params = {
                    **DEFAULT_PARAMS,
                    "fs": f"b:{theme['code']}",
                }

                # 获取题材股票
                stock_data = await self.fetch_json(EASTMONEY_API_BASE, stock_params)

                # 解析股票列表
                stocks = self.parse_theme_stocks(stock_data, theme["code"])

                # 保存股票关联
                if stocks:
                    saved_stocks = await self._save_theme_stocks(theme["code"], stocks)
                    total_stocks += saved_stocks

            except Exception as e:
                logger.error(f"[{self.source_name}] 处理题材 {theme['code']} 失败: {e}")
                # 继续处理其他题材，不中断
                continue

        logger.info(
            f"[{self.source_name}] 爬取任务完成: "
            f"保存 {saved_themes} 个题材, {total_stocks} 只股票"
        )

        return themes, saved_themes + total_stocks

    async def close(self) -> None:
        """关闭爬虫资源"""
        await self.middleware.close()
