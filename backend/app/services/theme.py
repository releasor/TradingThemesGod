"""题材服务

提供题材相关的业务逻辑。
"""

import time
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.theme import ThemeRepository
from app.repositories.theme_insight import ThemeInsightRepository
from app.schemas.common import calculate_total_pages
from app.schemas.stock import StockBrief, StockListResponse
from app.schemas.theme import (
    IndustryChainBrief,
    ThemeBrief,
    ThemeCategoriesResponse,
    ThemeDetailResponse,
    ThemeListResponse,
    ThemeRankingResponse,
)
from app.schemas.theme_insight import (
    ThemeDriverEventResponse,
    ThemeMarketSnapshotResponse,
    ThemeProfileResponse,
)
from app.services.concept_graph import ConceptGraphService

# 简单的内存缓存
_cache: dict[str, tuple[float, Any]] = {}
CACHE_TTL = 60  # 缓存有效期（秒）


def _get_cache(key: str) -> Any | None:
    """获取缓存值"""
    if key in _cache:
        timestamp, value = _cache[key]
        if time.time() - timestamp < CACHE_TTL:
            return value
        del _cache[key]
    return None


def _set_cache(key: str, value: Any) -> None:
    """设置缓存值"""
    _cache[key] = (time.time(), value)


def clear_cache() -> None:
    """清除所有缓存"""
    _cache.clear()


class ThemeService:
    """题材服务"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ThemeRepository(session)
        self.insights = ThemeInsightRepository(session)
        self.concept_graph = ConceptGraphService(session)

    async def list_themes(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "heat_index",
        sort_order: str = "desc",
        category: str | None = None,
        tags: str | None = None,
    ) -> ThemeListResponse:
        """获取题材列表（分页）

        Args:
            page: 页码
            page_size: 每页数量
            sort_by: 排序字段
            sort_order: 排序方向
            category: 分类筛选
            tags: 标签筛选

        Returns:
            分页题材列表
        """
        themes, total = await self.repo.list_paginated(
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            category=category,
            tags=tags,
        )

        return ThemeListResponse(
            items=[ThemeBrief.model_validate(t) for t in themes],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=calculate_total_pages(total, page_size),
        )

    async def get_theme_detail(self, theme_id: int) -> ThemeDetailResponse:
        """获取题材详情

        Args:
            theme_id: 题材ID

        Returns:
            题材详情（含产业链数据）

        Raises:
            HTTPException: 题材不存在
        """
        theme = await self.repo.get_by_id_with_chains(theme_id)
        if theme is None:
            raise HTTPException(status_code=404, detail="题材不存在")

        # 按层级分组产业链数据
        chains_by_level: dict[str, list[IndustryChainBrief]] = {
            "upstream": [],
            "midstream": [],
            "downstream": [],
        }
        for chain in theme.industry_chains:
            brief = IndustryChainBrief.model_validate(chain)
            chains_by_level[chain.level].append(brief)

        chain_stock_counts = await self.repo.count_stocks_by_chain_level(theme_id)
        concept_graph = await self.concept_graph.get_graph(theme_id)
        profile = await self.insights.get_profile(theme_id)
        events = await self.insights.list_recent_events(
            theme_id, now=datetime.now(UTC), limit=5
        )
        snapshot = await self.insights.get_latest_snapshot(theme_id)

        return ThemeDetailResponse(
            id=theme.id,
            name=theme.name,
            code=theme.code,
            description=theme.description,
            heat_index=theme.heat_index,
            rise_fall_pct=theme.rise_fall_pct,
            stock_count=theme.stock_count,
            category=theme.category,
            tags=theme.tags,
            source=theme.source,
            created_at=theme.created_at,
            updated_at=theme.updated_at,
            industry_chains=chains_by_level,
            chain_stock_counts=chain_stock_counts,
            concept_graph=concept_graph,
            profile=(ThemeProfileResponse.model_validate(profile) if profile else None),
            recent_driver_events=[
                ThemeDriverEventResponse.model_validate(event) for event in events
            ],
            market_snapshot=(
                ThemeMarketSnapshotResponse.model_validate(snapshot)
                if snapshot
                else None
            ),
        )

    async def search_themes(
        self,
        query: str,
        page: int = 1,
        page_size: int = 20,
    ) -> ThemeListResponse:
        """搜索题材

        Args:
            query: 搜索关键词
            page: 页码
            page_size: 每页数量

        Returns:
            搜索结果
        """
        themes, total = await self.repo.search(
            query=query,
            page=page,
            page_size=page_size,
        )

        return ThemeListResponse(
            items=[ThemeBrief.model_validate(t) for t in themes],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=calculate_total_pages(total, page_size),
        )

    async def get_categories(self) -> ThemeCategoriesResponse:
        """获取所有分类

        Returns:
            分类列表
        """
        # 检查缓存
        cache_key = "categories"
        cached = _get_cache(cache_key)
        if cached is not None:
            return cached

        categories = await self.repo.get_categories()
        result = ThemeCategoriesResponse(categories=categories)

        # 设置缓存（分类数据变化不频繁，缓存5分钟）
        _set_cache(cache_key, result)

        return result

    async def get_ranking(self, limit: int = 20) -> ThemeRankingResponse:
        """获取题材排名

        Args:
            limit: 返回数量

        Returns:
            排名列表
        """
        themes = await self.repo.get_ranking(limit=limit)
        return ThemeRankingResponse(
            items=[ThemeBrief.model_validate(t) for t in themes],
            limit=limit,
        )

    async def get_market_signals(self) -> ThemeRankingResponse:
        """获取独立展示的市场表现板块。"""
        themes = await self.repo.get_market_signals()
        return ThemeRankingResponse(
            items=[ThemeBrief.model_validate(theme) for theme in themes],
            limit=len(themes),
        )

    async def get_indicator_signals(self) -> ThemeRankingResponse:
        """获取独立展示的行情指标板块。"""
        themes = await self.repo.get_indicator_signals()
        return ThemeRankingResponse(
            items=[ThemeBrief.model_validate(theme) for theme in themes],
            limit=len(themes),
        )

    async def stream_export_csv(self, category: str | None = None):
        """流式导出题材 CSV（生成器，内存占用 O(1)）

        Args:
            category: 分类筛选

        Yields:
            CSV 行字符串（含表头）
        """
        import csv
        import io

        # 表头
        header = io.StringIO()
        csv.writer(header).writerow(
            [
                "题材名称",
                "题材代码",
                "分类",
                "热度指数",
                "涨跌幅(%)",
                "关联股票数",
                "数据来源",
            ]
        )
        yield header.getvalue()

        # 数据行：逐条生成，内存占用恒定
        async for theme in self.repo.stream_all(category=category):
            row = io.StringIO()
            csv.writer(row).writerow(
                [
                    theme.name,
                    theme.code,
                    theme.category or "",
                    float(theme.heat_index),
                    float(theme.rise_fall_pct),
                    theme.stock_count,
                    theme.source or "",
                ]
            )
            yield row.getvalue()

    async def get_theme_stocks(
        self,
        theme_id: int,
        chain_level: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> StockListResponse:
        """获取题材关联的股票列表

        Args:
            theme_id: 题材ID
            chain_level: 产业链层级筛选
            page: 页码
            page_size: 每页数量

        Returns:
            分页股票列表

        Raises:
            HTTPException: 题材不存在
        """
        # 先验证题材存在
        if not await self.repo.exists(theme_id):
            raise HTTPException(status_code=404, detail="题材不存在")

        stocks, total = await self.repo.get_stocks_by_theme(
            theme_id=theme_id,
            chain_level=chain_level,
            page=page,
            page_size=page_size,
        )

        return StockListResponse(
            items=[StockBrief.model_validate(s) for s in stocks],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=calculate_total_pages(total, page_size),
        )
