"""题材仓储

提供 Theme 的数据库查询操作。
"""

from math import ceil
from sqlalchemy import func, select, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.theme import Theme
from app.models.industry_chain import IndustryChain
from app.models.stock import Stock
from app.models.theme_stock import ThemeStock

# 允许排序的字段白名单
THEME_SORT_FIELDS = {
    "heat_index", "rise_fall_pct", "stock_count", "name",
}


class ThemeRepository:
    """题材仓储"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "heat_index",
        sort_order: str = "desc",
        category: str | None = None,
        tags: str | None = None,
    ) -> tuple[list[Theme], int]:
        """分页查询题材列表

        Args:
            page: 页码
            page_size: 每页数量
            sort_by: 排序字段
            sort_order: 排序方向
            category: 分类筛选
            tags: 标签筛选（逗号分隔）

        Returns:
            (题材列表, 总数)
        """
        # 基础查询：排除软删除
        base_query = select(Theme).where(Theme.deleted_at.is_(None))

        # 应用筛选
        if category:
            base_query = base_query.where(Theme.category == category)

        if tags:
            # JSONB 数组包含查询
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]
            for tag in tag_list:
                base_query = base_query.where(Theme.tags.contains([tag]))

        # 计算总数
        count_query = select(func.count()).select_from(base_query.subquery())
        total = (await self.session.execute(count_query)).scalar() or 0

        # 应用排序
        sort_column = getattr(Theme, sort_by, None)
        if sort_column is None or sort_by not in THEME_SORT_FIELDS:
            sort_column = Theme.heat_index
        if sort_order == "desc":
            base_query = base_query.order_by(desc(sort_column))
        else:
            base_query = base_query.order_by(asc(sort_column))

        # 应用分页
        offset = (page - 1) * page_size
        base_query = base_query.offset(offset).limit(page_size)

        # 执行查询
        result = await self.session.execute(base_query)
        themes = list(result.scalars().all())

        return themes, total

    async def get_by_id(self, theme_id: int) -> Theme | None:
        """获取题材详情（含产业链数据）

        Args:
            theme_id: 题材ID

        Returns:
            题材对象或 None
        """
        query = (
            select(Theme)
            .where(Theme.id == theme_id, Theme.deleted_at.is_(None))
            .options(selectinload(Theme.industry_chains))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def search(
        self,
        query: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Theme], int]:
        """搜索题材（名称和描述）

        Args:
            query: 搜索关键词
            page: 页码
            page_size: 每页数量

        Returns:
            (题材列表, 总数)
        """
        # 构建搜索条件
        search_pattern = f"%{query}%"
        search_condition = or_(
            Theme.name.ilike(search_pattern),
            Theme.description.ilike(search_pattern),
        )

        # 基础查询
        base_query = select(Theme).where(
            Theme.deleted_at.is_(None),
            search_condition,
        )

        # 计算总数
        count_query = select(func.count()).select_from(base_query.subquery())
        total = (await self.session.execute(count_query)).scalar() or 0

        # 应用排序和分页
        base_query = base_query.order_by(desc(Theme.heat_index))
        offset = (page - 1) * page_size
        base_query = base_query.offset(offset).limit(page_size)

        # 执行查询
        result = await self.session.execute(base_query)
        themes = list(result.scalars().all())

        return themes, total

    async def get_categories(self) -> list[str]:
        """获取所有唯一分类

        Returns:
            分类列表
        """
        query = (
            select(Theme.category)
            .where(Theme.deleted_at.is_(None), Theme.category.isnot(None))
            .distinct()
            .order_by(Theme.category)
        )
        result = await self.session.execute(query)
        return [row[0] for row in result.all() if row[0]]

    async def get_ranking(self, limit: int = 20) -> list[Theme]:
        """获取题材排名（按热度降序）

        Args:
            limit: 返回数量

        Returns:
            题材列表
        """
        query = (
            select(Theme)
            .where(Theme.deleted_at.is_(None))
            .order_by(desc(Theme.heat_index))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_industry_chains_by_theme(self, theme_id: int) -> list[IndustryChain]:
        """获取题材的产业链数据

        Args:
            theme_id: 题材ID

        Returns:
            产业链列表
        """
        query = (
            select(IndustryChain)
            .where(IndustryChain.theme_id == theme_id)
            .order_by(IndustryChain.sort_order)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_stocks_by_theme(
        self,
        theme_id: int,
        chain_level: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Stock], int]:
        """获取题材关联的股票列表（分页）

        Args:
            theme_id: 题材ID
            chain_level: 产业链层级筛选
            page: 页码
            page_size: 每页数量

        Returns:
            (股票列表, 总数)
        """
        base_query = (
            select(Stock)
            .join(ThemeStock, ThemeStock.stock_id == Stock.id)
            .where(ThemeStock.theme_id == theme_id)
        )

        if chain_level:
            base_query = base_query.where(ThemeStock.chain_level == chain_level)

        # 计算总数
        count_query = select(func.count()).select_from(base_query.subquery())
        total = (await self.session.execute(count_query)).scalar() or 0

        # 按 sort_order 排序
        base_query = base_query.order_by(asc(ThemeStock.sort_order))

        # 应用分页
        offset = (page - 1) * page_size
        base_query = base_query.offset(offset).limit(page_size)

        result = await self.session.execute(base_query)
        stocks = list(result.scalars().all())

        return stocks, total
