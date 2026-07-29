"""同花顺爬虫

- run(): 从同花顺网站获取单题材产业链结构（上游/中游/下游）
- collect_full/commit_full: 概念板块列表（全量竞速兜底，themes-only）
"""

import asyncio
import re
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Any

import akshare as ak
from sqlalchemy import select, tuple_

from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.models.industry_chain import IndustryChain
from app.models.theme import Theme
from app.scrapers.anti_scraping import AntiScrapingMiddleware
from app.scrapers.base import BaseScraper
from app.scrapers.draft_types import FullScrapeDraft

logger = get_logger(__name__)

# 同花顺产业链页面基础 URL
THS_CHAIN_BASE_URL = "http://q.10jqka.com.cn/thshy/detail/code/"

# 产业链层级映射
CHAIN_LEVEL_MAP = {
    "上游": "upstream",
    "中游": "midstream",
    "下游": "downstream",
}


class TongHuaShunScraper(BaseScraper):
    """同花顺产业链爬虫

    从同花顺网站获取产业链结构数据。
    """

    source_name = "ths"

    def __init__(self, middleware: AntiScrapingMiddleware | None = None):
        """初始化爬虫

        Args:
            middleware: 反爬虫中间件实例
        """
        super().__init__(middleware)

    def parse(self, html: str) -> list[dict[str, Any]]:
        """解析产业链页面内容

        Args:
            html: 页面 HTML

        Returns:
            产业链数据列表
        """
        chains = []

        if not html:
            logger.warning(f"[{self.source_name}] 空 HTML 内容")
            return chains

        try:
            # 解析产业链结构
            # 同花顺页面通常包含上游、中游、下游三个部分
            # 每个部分包含环节名称、描述和代表公司

            # 尝试提取产业链区块
            chain_blocks = self._extract_chain_blocks(html)

            for block in chain_blocks:
                level_cn = block.get("level", "")
                level = CHAIN_LEVEL_MAP.get(level_cn, "")

                if not level:
                    logger.warning(f"[{self.source_name}] 未知产业链层级: {level_cn}")
                    continue

                chain = {
                    "level": level,
                    "name": block.get("name", ""),
                    "description": block.get("description", ""),
                    "representative_companies": block.get("companies", []),
                }

                if chain["name"]:
                    chains.append(chain)
                else:
                    logger.warning(f"[{self.source_name}] 跳过无名称的产业链环节")

        except Exception as e:
            logger.error(f"[{self.source_name}] 解析产业链数据失败: {e}")

        logger.info(f"[{self.source_name}] 解析到 {len(chains)} 个产业链环节")
        return chains

    def _extract_chain_blocks(self, html: str) -> list[dict[str, Any]]:
        """从 HTML 提取产业链区块

        Args:
            html: 页面 HTML

        Returns:
            产业链区块列表
        """
        blocks = []

        # 尝试使用正则表达式提取产业链结构
        # 这是一个简化的实现，实际可能需要根据页面结构调整

        # 查找上游、中游、下游关键词
        for level_cn in ["上游", "中游", "下游"]:
            # 查找包含该关键词的区块
            pattern = rf'{level_cn}.*?(?=上游|中游|下游|$)'
            match = re.search(pattern, html, re.DOTALL)

            if match:
                block_text = match.group(0)

                # 提取环节名称（通常是第一个标题或链接）
                name_match = re.search(r'<a[^>]*>([^<]+)</a>', block_text)
                name = name_match.group(1).strip() if name_match else ""

                # 提取描述
                desc_match = re.search(r'<p[^>]*>([^<]+)</p>', block_text)
                description = desc_match.group(1).strip() if desc_match else ""

                # 提取代表公司
                companies = []
                company_matches = re.findall(r'<a[^>]*>([^<]+)</a>', block_text)
                for company in company_matches:
                    company = company.strip()
                    if company and company != name:
                        companies.append(company)

                blocks.append({
                    "level": level_cn,
                    "name": name or f"{level_cn}产业",
                    "description": description,
                    "companies": companies[:5],  # 限制最多5个代表公司
                })

        # 如果正则没有匹配到，尝试更宽松的解析
        if not blocks:
            # 尝试查找所有链接作为产业链环节
            links = re.findall(r'<a[^>]*href="[^"]*"[^>]*>([^<]+)</a>', html)
            for i, link in enumerate(links[:10]):  # 限制最多10个
                level_cn = ["上游", "中游", "下游"][i % 3]
                blocks.append({
                    "level": level_cn,
                    "name": link.strip(),
                    "description": "",
                    "companies": [],
                })

        return blocks

    async def save(self, data: list[dict[str, Any]]) -> int:
        """保存产业链数据（批量查询优化）

        Args:
            data: 产业链数据列表

        Returns:
            保存的记录数
        """
        saved_count = 0

        async with AsyncSessionLocal() as session:
            # 批量查询现有产业链记录（避免 N+1 查询）
            keys = [
                (d["theme_id"], d["level"])
                for d in data
                if d.get("theme_id") and d.get("level")
            ]
            if keys:
                existing_result = await session.execute(
                    select(IndustryChain).where(
                        tuple_(IndustryChain.theme_id, IndustryChain.level).in_(keys)
                    )
                )
                existing_map = {
                    (c.theme_id, c.level): c
                    for c in existing_result.scalars().all()
                }
            else:
                existing_map = {}

            for chain_data in data:
                try:
                    key = (chain_data.get("theme_id"), chain_data["level"])
                    chain = existing_map.get(key)

                    if chain:
                        # 更新现有记录
                        chain.name = chain_data["name"]
                        chain.description = chain_data.get("description")
                        chain.representative_companies = chain_data.get("representative_companies")
                        logger.debug(
                            f"[{self.source_name}] 更新产业链环节: {chain_data['name']}"
                        )
                    else:
                        # 创建新记录
                        chain = IndustryChain(
                            theme_id=chain_data.get("theme_id"),
                            level=chain_data["level"],
                            name=chain_data["name"],
                            description=chain_data.get("description"),
                            representative_companies=chain_data.get("representative_companies"),
                            sort_order=saved_count,
                        )
                        session.add(chain)
                        logger.debug(
                            f"[{self.source_name}] 创建产业链环节: {chain_data['name']}"
                        )

                    saved_count += 1

                except Exception as e:
                    logger.error(
                        f"[{self.source_name}] 保存产业链环节失败: {e}, "
                        f"数据: {chain_data}"
                    )
                    continue

            await session.commit()

        logger.info(f"[{self.source_name}] 保存了 {saved_count} 个产业链环节")
        return saved_count

    @staticmethod
    def _normalize_concept_code(code: Any) -> str:
        """同花顺概念代码加 THS 前缀，避免与东财 BK / 股票代码冲突。"""
        value = str(code or "").strip().upper()
        if not value:
            return ""
        if value.startswith("THS"):
            return value
        return f"THS{value}"

    def _parse_concept_themes(self, frame: Any) -> list[dict[str, Any]]:
        """解析同花顺概念板块列表为题材草稿（不含成分股）。"""
        themes: list[dict[str, Any]] = []
        if frame is None or getattr(frame, "empty", True):
            return themes

        columns = set(getattr(frame, "columns", []))
        code_column = "code" if "code" in columns else ("板块代码" if "板块代码" in columns else None)
        name_column = "name" if "name" in columns else ("板块名称" if "板块名称" in columns else None)
        if code_column is None or name_column is None:
            logger.warning(
                f"[{self.source_name}] 概念列表缺少 code/name 列: {list(columns)}"
            )
            return themes

        for _, row in frame.iterrows():
            code = self._normalize_concept_code(row.get(code_column))
            name = str(row.get(name_column, "")).strip()
            if not code or not name:
                continue
            themes.append(
                {
                    "name": name,
                    "code": code,
                    "heat_index": None,
                    "rise_fall_pct": None,
                    "stock_count": None,
                    "category": None,
                    "source": self.source_name,
                }
            )
        return themes

    async def collect_full(
        self,
        cancel: asyncio.Event | None = None,
        params: dict[str, Any] | None = None,
        on_progress: Callable[[float], None] | None = None,
    ) -> FullScrapeDraft:
        """采集同花顺概念题材草稿（themes-only），供全量竞速兜底。"""
        del params

        def report(pct: float) -> None:
            if on_progress is not None:
                on_progress(max(0.0, min(100.0, pct)))

        if cancel is not None and cancel.is_set():
            raise asyncio.CancelledError()

        logger.info(f"[{self.source_name}] 开始全量题材采集（同花顺概念板块，不落库）")
        report(10.0)
        last_error: Exception | None = None
        frame = None
        for attempt in range(1, 4):
            if cancel is not None and cancel.is_set():
                raise asyncio.CancelledError()
            try:
                frame = await asyncio.to_thread(ak.stock_board_concept_name_ths)
                last_error = None
                break
            except Exception as e:
                last_error = e
                logger.warning(
                    f"[{self.source_name}] 获取概念板块失败（第 {attempt}/3 次）: {e}"
                )
                if attempt < 3:
                    await asyncio.sleep(1.5 * attempt)

        if last_error is not None or frame is None:
            logger.error(f"[{self.source_name}] 获取概念板块失败: {last_error}")
            raise last_error or RuntimeError("获取同花顺概念板块失败")

        if cancel is not None and cancel.is_set():
            raise asyncio.CancelledError()

        report(80.0)
        themes = self._parse_concept_themes(frame)
        logger.info(f"[{self.source_name}] 解析到 {len(themes)} 个概念题材")
        report(100.0)
        return FullScrapeDraft(
            source=self.source_name,
            trade_date=date.today() if themes else None,
            themes=themes,
            stocks_by_code={},
        )

    async def _save_themes(self, themes: list[dict[str, Any]]) -> int:
        """幂等保存题材数据。"""
        saved_count = 0
        async with AsyncSessionLocal() as session:
            theme_codes = [t["code"] for t in themes if t.get("code")]
            from app.scrapers.theme_upsert import load_themes_map_for_source

            existing_map = await load_themes_map_for_source(
                session, source=self.source_name, codes=theme_codes
            )

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
        return await self._save_themes(draft.themes)

    async def run(
        self, url: str = "", params: dict[str, Any] | None = None
    ) -> tuple[list[dict[str, Any]], int]:
        """执行完整爬虫生命周期

        Args:
            url: 未使用（使用默认 URL）
            params: 额外参数，必须包含本地 theme_code 和同花顺 source_code

        Returns:
            (产业链数据列表, 保存的记录数) 元组
        """
        logger.info(f"[{self.source_name}] 开始爬取产业链数据")

        theme_code = str(params.get("theme_code", "")).strip() if params else ""
        if not theme_code:
            raise ValueError("未提供本地题材代码 theme_code")

        source_code = str(params.get("source_code", "")).strip() if params else ""
        if not source_code:
            raise ValueError("未提供同花顺代码 source_code")

        # 构建请求 URL
        request_url = f"{THS_CHAIN_BASE_URL}{source_code}"

        try:
            # Step 1: 获取页面内容
            response = await self.middleware.get(request_url)
            response.raise_for_status()
            expected_path = f"/thshy/detail/code/{source_code}"
            if response.url.path.rstrip("/") != expected_path:
                raise ValueError("同花顺代码无效或页面已重定向")

            html = response.text
            logger.info(f"[{self.source_name}] 获取到 {len(html)} 字节")

            # Step 2: 解析产业链数据
            chains = self.parse(html)
            logger.info(f"[{self.source_name}] 解析到 {len(chains)} 个产业链环节")

            if not chains:
                logger.warning(f"[{self.source_name}] 未获取到产业链数据")
                return [], 0

            # 查询题材 ID
            async with AsyncSessionLocal() as session:
                theme_result = await session.execute(
                    select(Theme).where(Theme.code == theme_code, Theme.deleted_at.is_(None))
                )
                theme = theme_result.scalar_one_or_none()

                if not theme:
                    logger.error(f"[{self.source_name}] 未找到题材: {theme_code}")
                    return chains, 0

                # 设置 theme_id
                for chain in chains:
                    chain["theme_id"] = theme.id

            # Step 3: 保存产业链数据
            saved_count = await self.save(chains)

            logger.info(
                f"[{self.source_name}] 爬取任务完成: 保存 {saved_count} 个产业链环节"
            )

            return chains, saved_count

        except Exception as e:
            logger.error(f"[{self.source_name}] 爬取产业链数据失败: {e}")
            raise

    async def close(self) -> None:
        """关闭爬虫资源"""
        await self.middleware.close()
