"""AKShare 股票数据爬虫

使用 AKShare Python 库获取股票基本信息。
全量题材竞速：collect_full 仅采集概念板块列表（无成分股），commit_full 落库题材。
"""

import asyncio
import json
import math
import re
from datetime import date
from decimal import Decimal
from typing import Any

import akshare as ak
import requests
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.models.stock import Stock
from app.models.theme import Theme
from app.scrapers.anti_scraping import AntiScrapingMiddleware
from app.scrapers.base import BaseScraper
from app.scrapers.draft_types import FullScrapeDraft

logger = get_logger(__name__)


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

    @staticmethod
    def _to_decimal(value: Any) -> Decimal | None:
        """将来源数值转换为 Decimal，无效值保持为空。"""
        try:
            result = Decimal(str(value))
            return result if result.is_finite() else None
        except Exception:
            return None

    def _normalize_spot_row(self, row: Any) -> dict[str, Any] | None:
        """统一新浪 A 股行情字段。"""
        raw_code = str(row.get("代码", "")).strip().lower()
        code = re.sub(r"^(sh|sz|bj)", "", raw_code)
        name = str(row.get("名称", "")).strip()
        if not code or not name:
            return None
        return {
            "code": code,
            "name": name,
            "current_price": self._to_decimal(row.get("最新价")),
            "rise_fall_pct": self._to_decimal(row.get("涨跌幅")),
            "exchange": self._detect_exchange(code),
        }

    def _parse_tencent_quotes(self, text: str) -> dict[str, Decimal]:
        """解析腾讯批量行情中的总市值，来源单位为亿元。"""
        market_caps: dict[str, Decimal] = {}
        for line in text.splitlines():
            match = re.search(r'="(.*)";', line)
            if not match:
                continue
            fields = match.group(1).split("~")
            if len(fields) <= 44:
                continue
            market_cap_yi = self._to_decimal(fields[44])
            code = fields[2].strip()
            if code and market_cap_yi is not None and market_cap_yi > 0:
                market_caps[code] = market_cap_yi * Decimal("100000000")
        return market_caps

    def _fetch_tencent_market_caps(self, codes: list[str]) -> dict[str, Decimal]:
        """分批获取总市值，避免逐股请求。"""
        result: dict[str, Decimal] = {}
        headers = {"Referer": "https://gu.qq.com", "User-Agent": "Mozilla/5.0"}
        for offset in range(0, len(codes), 100):
            symbols = [
                f"{self._detect_exchange(code).lower()}{code}"
                for code in codes[offset : offset + 100]
            ]
            response = requests.get(
                f"https://qt.gtimg.cn/q={','.join(symbols)}",
                headers=headers,
                timeout=15,
            )
            response.raise_for_status()
            response.encoding = "gbk"
            result.update(self._parse_tencent_quotes(response.text))
        return result

    def _fetch_sina_industries(self) -> tuple[dict[str, str], dict[str, Decimal]]:
        """批量构建新浪行业归属，并读取接口附带的总市值。"""
        headers = {
            "Referer": "https://finance.sina.com.cn",
            "User-Agent": "Mozilla/5.0",
        }
        response = requests.get(
            "https://vip.stock.finance.sina.com.cn/q/view/newSinaHy.php",
            headers=headers,
            timeout=15,
        )
        response.raise_for_status()
        sectors = json.loads(response.text[response.text.find("{") :])
        industries: dict[str, str] = {}
        market_caps: dict[str, Decimal] = {}
        detail_url = "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"
        for sector, summary in sectors.items():
            values = summary.split(",")
            industry, total = values[1].strip(), int(values[2])
            for page in range(1, math.ceil(total / 80) + 1):
                detail = requests.get(
                    detail_url,
                    params={
                        "page": page,
                        "num": 80,
                        "sort": "symbol",
                        "asc": 1,
                        "node": sector,
                    },
                    headers=headers,
                    timeout=15,
                )
                detail.raise_for_status()
                for item in detail.json() or []:
                    code = str(item.get("code", "")).strip()
                    if not code:
                        continue
                    industries.setdefault(code, industry)
                    market_cap_wan = self._to_decimal(item.get("mktcap"))
                    if market_cap_wan is not None and market_cap_wan > 0:
                        market_caps[code] = market_cap_wan * Decimal("10000")
        return industries, market_caps

    async def fetch_stock_info(self) -> list[dict[str, Any]]:
        """获取股票基本信息

        Returns:
            股票数据列表
        """
        logger.info(f"[{self.source_name}] 开始获取股票信息")

        try:
            # 完整目录负责股票覆盖，实时快照只负责补充行情字段。
            # 停牌、除权等股票可能暂时不出现在实时快照中。
            catalog_df, spot_df = await asyncio.gather(
                asyncio.to_thread(ak.stock_info_a_code_name),
                asyncio.to_thread(ak.stock_zh_a_spot),
            )

            if catalog_df is None or catalog_df.empty:
                logger.warning(f"[{self.source_name}] 未获取到股票数据")
                return []

            # 转换为字典列表
            industries, sina_market_caps = await asyncio.to_thread(
                self._fetch_sina_industries
            )
            live_by_code: dict[str, dict[str, Any]] = {}
            if spot_df is not None and not spot_df.empty:
                normalized_rows = [
                    self._normalize_spot_row(row) for _, row in spot_df.iterrows()
                ]
                live_by_code = {
                    row["code"]: row for row in normalized_rows if row is not None
                }

            valid_rows: list[dict[str, Any]] = []
            for _, row in catalog_df.iterrows():
                code = re.sub(r"^(sh|sz|bj)", "", str(row.get("code", "")).strip().lower())
                name = str(row.get("name", "")).strip()
                if not code or not name:
                    continue
                live = live_by_code.get(code, {})
                valid_rows.append(
                    {
                        "code": code,
                        "name": name,
                        "current_price": live.get("current_price"),
                        "rise_fall_pct": live.get("rise_fall_pct"),
                        "exchange": self._detect_exchange(code),
                    }
                )
            try:
                tencent_market_caps = await asyncio.to_thread(
                    self._fetch_tencent_market_caps,
                    [row["code"] for row in valid_rows],
                )
            except Exception as exc:
                logger.warning(f"[{self.source_name}] 腾讯市值补充失败: {exc}")
                tencent_market_caps = {}

            stocks = []
            for stock in valid_rows:
                try:
                    code = stock["code"]
                    stock["industry"] = industries.get(code)
                    stock["market_cap"] = (
                        sina_market_caps.get(code) or tencent_market_caps.get(code)
                    )

                    # 验证必填字段
                    if stock["code"] and stock["name"]:
                        stocks.append(stock)
                    else:
                        logger.warning(f"[{self.source_name}] 跳过无效股票数据: {stock}")

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
        """保存股票数据（幂等更新，批量查询优化）

        Args:
            data: 股票数据列表

        Returns:
            保存的记录数
        """
        saved_count = 0

        async with AsyncSessionLocal() as session:
            # 批量查询现有股票（避免 N+1 查询）
            stock_codes = [s["code"] for s in data if s.get("code")]
            try:
                if stock_codes:
                    existing_result = await session.execute(
                        select(Stock).where(Stock.code.in_(stock_codes))
                    )
                    existing_map = {
                        s.code: s for s in existing_result.scalars().all()
                    }
                else:
                    existing_map = {}
            except Exception as exc:
                logger.error(f"[{self.source_name}] 查询现有股票失败: {exc}")
                return 0

            for stock_data in data:
                try:
                    stock = existing_map.get(stock_data["code"])

                    if stock:
                        # 更新现有记录（AKShare 为权威来源）
                        stock.name = stock_data["name"]
                        if stock_data.get("industry"):
                            stock.industry = stock_data["industry"]
                        if stock_data.get("market_cap") is not None:
                            stock.market_cap = stock_data["market_cap"]
                        if stock_data.get("exchange"):
                            stock.exchange = stock_data["exchange"]
                        if stock_data.get("current_price") is not None:
                            stock.current_price = stock_data["current_price"]
                        if stock_data.get("rise_fall_pct") is not None:
                            stock.rise_fall_pct = stock_data["rise_fall_pct"]
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
                            current_price=stock_data.get("current_price"),
                            rise_fall_pct=stock_data.get("rise_fall_pct"),
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

    @staticmethod
    def _normalize_board_code(code: str) -> str:
        value = str(code).strip().upper()
        return value if value.startswith("BK") else f"BK{value}"

    @staticmethod
    def _to_optional_decimal(value: Any) -> Decimal | None:
        if value is None or value == "":
            return None
        try:
            result = Decimal(str(value))
            return result if result.is_finite() else None
        except Exception:
            return None

    def _parse_concept_themes(self, frame: Any) -> list[dict[str, Any]]:
        """解析 AKShare 概念板块列表为题材草稿（不含成分股）。"""
        themes: list[dict[str, Any]] = []
        if frame is None or getattr(frame, "empty", True):
            return themes
        code_column = "板块代码" if "板块代码" in frame.columns else None
        if code_column is None:
            return themes

        for _, row in frame.iterrows():
            code = self._normalize_board_code(row[code_column])
            name = str(row.get("板块名称", "")).strip()
            if not name:
                continue
            rise_fall_pct = row.get("涨跌幅")
            heat_index = row.get("换手率")
            up_count = row.get("上涨家数")
            stock_count = None
            if up_count is not None:
                try:
                    down_count = int(row.get("下跌家数") or 0)
                    stock_count = int(up_count) + down_count
                except (TypeError, ValueError):
                    stock_count = None
            themes.append(
                {
                    "name": name,
                    "code": code,
                    "heat_index": self._to_optional_decimal(heat_index),
                    "rise_fall_pct": self._to_optional_decimal(rise_fall_pct),
                    "stock_count": stock_count,
                    "category": None,
                    "source": self.source_name,
                }
            )
        return themes

    async def collect_full(
        self,
        cancel: asyncio.Event | None = None,
        params: dict[str, Any] | None = None,
    ) -> FullScrapeDraft:
        """采集概念题材草稿（themes-only），不落库、不抓成分股。

        AKShare 调度器路径仍用 run() 拉全市场股票；本方法供全量竞速：
        题材非空即可作为可胜出草稿（stocks_by_code 为空）。
        """
        del params  # 保留与 EastMoney 一致的签名
        if cancel is not None and cancel.is_set():
            raise asyncio.CancelledError()

        logger.info(f"[{self.source_name}] 开始全量题材采集（概念板块，不落库）")
        try:
            frame = await asyncio.to_thread(ak.stock_board_concept_name_em)
        except Exception as e:
            logger.error(f"[{self.source_name}] 获取概念板块失败: {e}")
            raise

        if cancel is not None and cancel.is_set():
            raise asyncio.CancelledError()

        themes = self._parse_concept_themes(frame)
        logger.info(f"[{self.source_name}] 解析到 {len(themes)} 个概念题材")
        return FullScrapeDraft(
            source=self.source_name,
            trade_date=date.today() if themes else None,
            themes=themes,
            stocks_by_code={},
        )

    async def _save_themes(self, themes: list[dict[str, Any]]) -> int:
        """幂等保存题材数据（与东财路径对齐的 Theme upsert）。"""
        saved_count = 0
        async with AsyncSessionLocal() as session:
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
                        theme.name = theme_data["name"]
                        theme.code = theme_data["code"]
                        if theme_data.get("heat_index") is not None:
                            theme.heat_index = theme_data["heat_index"]
                        if theme_data.get("rise_fall_pct") is not None:
                            theme.rise_fall_pct = theme_data["rise_fall_pct"]
                        if theme_data.get("stock_count") is not None:
                            theme.stock_count = theme_data["stock_count"]
                        if theme_data.get("category") is not None:
                            theme.category = theme_data["category"]
                        theme.source = theme_data.get("source", self.source_name)
                    else:
                        theme = Theme(
                            name=theme_data["name"],
                            code=theme_data["code"],
                            heat_index=theme_data.get("heat_index") or Decimal("0"),
                            rise_fall_pct=theme_data.get("rise_fall_pct")
                            or Decimal("0"),
                            stock_count=theme_data.get("stock_count") or 0,
                            category=theme_data.get("category"),
                            source=theme_data.get("source", self.source_name),
                        )
                        session.add(theme)
                    saved_count += 1
                except Exception as e:
                    logger.error(
                        f"[{self.source_name}] 保存题材失败: {e}, 数据: {theme_data}"
                    )
                    continue

            await session.commit()

        logger.info(f"[{self.source_name}] 保存了 {saved_count} 个题材")
        return saved_count

    async def commit_full(self, draft: FullScrapeDraft) -> int:
        """落库全量题材草稿（当前无成分股）。"""
        if not draft.themes:
            return 0
        saved = await self._save_themes(draft.themes)
        # stocks_by_code 预留：当前 collect_full 不采成分股
        return saved

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
