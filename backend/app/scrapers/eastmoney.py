"""东方财富题材爬虫

从东方财富 API 获取题材概念列表和关联股票数据。
"""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.models.stock import Stock
from app.models.theme import Theme
from app.models.theme_stock import ThemeStock
from app.scrapers.anti_scraping import AntiScrapingMiddleware
from app.scrapers.base import BaseScraper
from app.services.theme_market import ThemeMarketService

logger = get_logger(__name__)

# 东方财富 API 基础配置
EASTMONEY_API_BASE = "https://push2.eastmoney.com/api/qt/clist/get"
EASTMONEY_API_FALLBACK_BASE = "https://push2delay.eastmoney.com/api/qt/clist/get"
EASTMONEY_API_BASES = (EASTMONEY_API_BASE, EASTMONEY_API_FALLBACK_BASE)

# 默认请求参数
DEFAULT_PARAMS = {
    "fid": "f3",
    "pn": "1",
    "po": "1",
    "pz": "100",  # 东方财富接口单页最多稳定返回 100 条
    "np": "1",
    "fltt": "2",
    "invt": "2",
    "ut": "7eea3edcaed734bea9cbfc24409ed989",
    "fields": "f2,f3,f8,f12,f14,f20,f100,f104,f124",
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
        self._active_api_base = EASTMONEY_API_BASE

    async def fetch_json(self, url: str, params: dict[str, Any] | None = None) -> dict:
        """获取 JSON API 数据

        Args:
            url: API URL
            params: 请求参数

        Returns:
            解析后的 JSON 数据
        """
        candidate_urls = [url]
        if url in EASTMONEY_API_BASES:
            candidate_urls = [
                self._active_api_base,
                *[
                    api_url
                    for api_url in EASTMONEY_API_BASES
                    if api_url != self._active_api_base
                ],
            ]

        last_error: Exception | None = None
        for candidate_url in candidate_urls:
            try:
                logger.info(f"[{self.source_name}] 正在请求 API: {candidate_url}")
                response = await self.middleware.get(candidate_url, params=params)
                response.raise_for_status()
                if candidate_url in EASTMONEY_API_BASES:
                    self._active_api_base = candidate_url
                return response.json()
            except Exception as exc:
                last_error = exc
                if candidate_url == candidate_urls[-1]:
                    break
                logger.warning(
                    f"[{self.source_name}] API {candidate_url} 请求失败，切换备用域名: {exc}"
                )

        if last_error is not None:
            raise last_error
        raise RuntimeError("东方财富 API 请求失败")

    async def fetch_all_pages(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        """按接口总数分页抓取全部数据"""
        page = 1
        page_size = int(params.get("pz", DEFAULT_PARAMS["pz"]))
        total: int | None = None
        items: list[dict[str, Any]] = []
        seen_codes: set[str] = set()

        while True:
            page_params = {**params, "pn": str(page)}
            payload = await self.fetch_json(url, page_params)
            data = payload.get("data") or {}
            page_items = data.get("diff") or []

            if total is None:
                try:
                    total = int(data.get("total", 0))
                except (TypeError, ValueError):
                    total = 0

            for item in page_items:
                code = str(item.get("f12", ""))
                if code and code in seen_codes:
                    continue
                if code:
                    seen_codes.add(code)
                items.append(item)

            if (
                not page_items
                or (total > 0 and len(items) >= total)
                or len(page_items) < page_size
            ):
                break

            page += 1

        return {
            "data": {
                "total": total or len(items),
                "diff": items,
            }
        }

    def parse_theme_list(self, data: dict) -> list[dict[str, Any]]:
        """解析题材列表数据

        Args:
            data: API 返回的 JSON 数据

        Returns:
            题材数据列表
        """
        themes = []
        diff = (data.get("data") or {}).get("diff", [])

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
                    "heat_index": self._to_optional_decimal(item.get("f8")),
                    "rise_fall_pct": self._to_optional_decimal(item.get("f3")),
                    "stock_count": self._to_optional_int(item.get("f104")),
                    "category": self._extract_category(item.get("f14", "")),  # 分类
                    "source": self.source_name,
                }

                # 验证必填字段
                if theme["name"] and theme["code"]:
                    themes.append(theme)
                else:
                    logger.warning(f"[{self.source_name}] 跳过无效题材数据: {item}")

            except (ValueError, TypeError) as e:
                logger.warning(
                    f"[{self.source_name}] 解析题材数据失败: {e}, 数据: {item}"
                )
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
        diff = (data.get("data") or {}).get("diff", [])

        if not diff:
            logger.info(f"[{self.source_name}] 题材 {theme_code} 无关联股票")
            return stocks

        for item in diff:
            try:
                stock = {
                    "code": str(item.get("f12", "")),  # 股票代码
                    "name": item.get("f14", ""),  # 股票名称
                    "rise_fall_pct": self._to_optional_decimal(item.get("f3")),
                    "current_price": self._to_optional_decimal(item.get("f2")),
                }
                market_cap = self._to_optional_decimal(item.get("f20"))
                industry = str(item.get("f100") or "").strip()
                if market_cap is not None:
                    stock["market_cap"] = market_cap
                if industry:
                    stock["industry"] = industry

                # 验证必填字段
                if stock["code"] and stock["name"]:
                    stocks.append(stock)
                else:
                    logger.warning(f"[{self.source_name}] 跳过无效股票数据: {item}")

            except (ValueError, TypeError) as e:
                logger.warning(
                    f"[{self.source_name}] 解析股票数据失败: {e}, 数据: {item}"
                )
                continue

        logger.info(
            f"[{self.source_name}] 题材 {theme_code} 解析到 {len(stocks)} 只股票"
        )
        return stocks

    @staticmethod
    def _to_decimal(value: Any) -> Decimal:
        """将东方财富的数值字段转换为 Decimal，缺失行情按 0 处理。"""
        if value in (None, "", "-"):
            return Decimal("0")

        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return Decimal("0")

    @staticmethod
    def _to_optional_decimal(value: Any) -> Decimal | None:
        """转换可选数值；来源缺失时保留 None，供增量更新判断。"""
        if value in (None, "", "-"):
            return None

        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return None

    @staticmethod
    def _to_optional_int(value: Any) -> int | None:
        """转换可选整数；无效来源值不应被解释为零。"""
        if value in (None, "", "-"):
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _extract_trade_date(data: dict[str, Any]) -> date | None:
        """从行情更新时间提取最近有效交易日，避免用服务器日历日期造快照。"""
        trade_dates: list[date] = []
        for item in (data.get("data") or {}).get("diff", []):
            raw_timestamp = item.get("f124")
            try:
                timestamp = int(raw_timestamp)
                if timestamp <= 0:
                    continue
                trade_dates.append(
                    datetime.fromtimestamp(timestamp, ZoneInfo("Asia/Shanghai")).date()
                )
            except (OSError, OverflowError, TypeError, ValueError):
                continue
        return max(trade_dates, default=None)

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
            # 题材代码是唯一且稳定的标识，名称可能随来源调整
            theme_codes = [t["code"] for t in themes if t.get("code")]
            existing_result = await session.execute(
                select(Theme).where(
                    Theme.code.in_(theme_codes),
                    Theme.deleted_at.is_(None),
                )
            )
            existing_map = {t.code: t for t in existing_result.scalars().all()}

            for theme_data in themes:
                try:
                    theme = existing_map.get(theme_data["code"])

                    if theme:
                        # 更新现有题材
                        theme.name = theme_data["name"]
                        theme.code = theme_data["code"]
                        if theme_data["heat_index"] is not None:
                            theme.heat_index = theme_data["heat_index"]
                        if theme_data["rise_fall_pct"] is not None:
                            theme.rise_fall_pct = theme_data["rise_fall_pct"]
                        if theme_data["stock_count"] is not None:
                            theme.stock_count = theme_data["stock_count"]
                        theme.category = theme_data["category"]
                        theme.source = theme_data["source"]
                        logger.debug(
                            f"[{self.source_name}] 更新题材: {theme_data['name']}"
                        )
                    else:
                        # 创建新题材
                        theme = Theme(
                            name=theme_data["name"],
                            code=theme_data["code"],
                            heat_index=theme_data["heat_index"] or Decimal("0"),
                            rise_fall_pct=theme_data["rise_fall_pct"] or Decimal("0"),
                            stock_count=theme_data["stock_count"] or 0,
                            category=theme_data["category"],
                            source=theme_data["source"],
                        )
                        session.add(theme)
                        logger.debug(
                            f"[{self.source_name}] 创建题材: {theme_data['name']}"
                        )

                    saved_count += 1

                except Exception as e:
                    logger.error(
                        f"[{self.source_name}] 保存题材失败: {e}, 数据: {theme_data}"
                    )
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
                select(Theme).where(
                    Theme.code == theme_code, Theme.deleted_at.is_(None)
                )
            )
            theme = theme_result.scalar_one_or_none()

            if not theme:
                logger.warning(f"[{self.source_name}] 未找到题材: {theme_code}")
                return 0

            # 以实际抓取结果为准，避免源列表统计口径与成分股详情不一致
            theme.stock_count = len(stocks)

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
                theme_stock_map = {
                    ts.stock_id: ts for ts in theme_stock_result.scalars().all()
                }
            else:
                theme_stock_map = {}

            for stock_data in stocks:
                try:
                    stock = stock_map.get(stock_data["code"])

                    if not stock:
                        # 创建新股票
                        stock = Stock(
                            market_cap=stock_data.get("market_cap"),
                            industry=stock_data.get("industry"),
                            code=stock_data["code"],
                            name=stock_data["name"],
                            current_price=stock_data.get("current_price"),
                            rise_fall_pct=stock_data.get("rise_fall_pct"),
                        )
                        session.add(stock)
                        await session.flush()  # 获取 stock.id
                        stock_map[stock_data["code"]] = stock
                    else:
                        stock.name = stock_data["name"]
                        stock.current_price = stock_data.get("current_price")
                        stock.rise_fall_pct = stock_data.get("rise_fall_pct")
                        if stock_data.get("market_cap") is not None:
                            stock.market_cap = stock_data["market_cap"]
                        if stock_data.get("industry"):
                            stock.industry = stock_data["industry"]

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

        logger.info(
            f"[{self.source_name}] 题材 {theme_code} 保存了 {saved_count} 只股票"
        )
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
        theme_params = {
            **DEFAULT_PARAMS,
            "fid": "f12",
            "fs": "m:90+t:3+f:!50",
        }
        if params:
            theme_params.update(params)

        try:
            theme_data = await self.fetch_all_pages(EASTMONEY_API_BASE, theme_params)
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
        latest_trade_date: date | None = None
        for theme in themes:
            try:
                # 构建题材股票请求参数
                stock_params = {
                    **DEFAULT_PARAMS,
                    "fid": "f12",
                    "fs": f"b:{theme['code']}",
                }

                # 获取题材股票
                stock_data = await self.fetch_all_pages(
                    EASTMONEY_API_BASE, stock_params
                )
                stock_trade_date = self._extract_trade_date(stock_data)
                if stock_trade_date is not None and (
                    latest_trade_date is None or stock_trade_date > latest_trade_date
                ):
                    latest_trade_date = stock_trade_date

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

        if latest_trade_date is None:
            logger.warning(
                f"[{self.source_name}] 行情缺少有效交易时间，跳过市场快照刷新"
            )
        else:
            try:
                await self._refresh_market_snapshots(latest_trade_date)
            except Exception as exc:
                logger.warning(f"[{self.source_name}] 题材市场快照刷新失败: {exc}")

        return themes, saved_themes + total_stocks

    async def close(self) -> None:
        """关闭爬虫资源"""
        await self.middleware.close()

    async def _refresh_market_snapshots(self, trade_date: date) -> int:
        async with AsyncSessionLocal() as session:
            return await ThemeMarketService(session).refresh_all(trade_date)
