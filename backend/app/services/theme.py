"""题材服务

提供题材相关的业务逻辑。
"""

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.theme import ThemeRepository
from app.schemas.theme import (
    ThemeBrief,
    ThemeCategoriesResponse,
    ThemeDetailResponse,
    ThemeListResponse,
    ThemeRankingResponse,
    IndustryChainBrief,
)
from app.schemas.stock import StockBrief, StockListResponse
from app.schemas.common import calculate_total_pages


class ThemeService:
    """题材服务"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ThemeRepository(session)

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
        theme = await self.repo.get_by_id(theme_id)
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
        categories = await self.repo.get_categories()
        return ThemeCategoriesResponse(categories=categories)

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
        theme = await self.repo.get_by_id(theme_id)
        if theme is None:
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
