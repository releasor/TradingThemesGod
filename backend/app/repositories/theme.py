"""题材仓储

提供 Theme 的数据库查询操作。
"""

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.theme_classification import (
    exclude_market_signals,
    only_indicator_signals,
    only_market_signals,
)
from app.models.industry_chain import IndustryChain
from app.models.stock import Stock
from app.models.theme import Theme
from app.models.theme_stock import ThemeStock
from app.repositories.base import BaseRepository

# 允许排序的字段白名单
THEME_SORT_FIELDS = {
    "heat_index",
    "rise_fall_pct",
    "stock_count",
    "name",
}


def _escape_like(value: str) -> str:
    """转义 LIKE 查询中的特殊字符（% 和 _），防止注入"""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _tag_contains(tag: str):
    """构建 MySQL JSON 数组成员匹配条件。"""
    return func.json_contains(Theme.tags, func.json_quote(tag)) == 1


class ThemeRepository(BaseRepository):
    """题材仓储"""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

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
        base_query = select(Theme).where(
            Theme.deleted_at.is_(None), exclude_market_signals()
        )

        # 应用筛选
        if category:
            base_query = base_query.where(Theme.category == category)

        if tags:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]
            for tag in tag_list:
                base_query = base_query.where(_tag_contains(tag))

        # 确定排序列
        sort_column = getattr(Theme, sort_by, None)
        if sort_column is None or sort_by not in THEME_SORT_FIELDS:
            sort_column = Theme.heat_index

        return await self._paginate(
            query=base_query,
            page=page,
            page_size=page_size,
            sort_column=sort_column,
            sort_order=sort_order,
        )

    async def get_by_id(self, theme_id: int) -> Theme | None:
        """获取题材详情（不含关联数据）

        Args:
            theme_id: 题材ID

        Returns:
            题材对象或 None
        """
        query = select(Theme).where(Theme.id == theme_id, Theme.deleted_at.is_(None))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_id_with_chains(self, theme_id: int) -> Theme | None:
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

    async def exists(self, theme_id: int) -> bool:
        """轻量级检查题材是否存在（不加载完整对象）

        Args:
            theme_id: 题材ID

        Returns:
            是否存在
        """
        query = (
            select(Theme.id)
            .where(Theme.id == theme_id, Theme.deleted_at.is_(None))
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

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
        search_pattern = f"%{_escape_like(query)}%"
        search_condition = or_(
            Theme.name.like(search_pattern, escape="\\"),
            Theme.description.like(search_pattern, escape="\\"),
        )

        # 基础查询
        base_query = select(Theme).where(
            Theme.deleted_at.is_(None),
            exclude_market_signals(),
            search_condition,
        )

        return await self._paginate(
            query=base_query,
            page=page,
            page_size=page_size,
            sort_column=Theme.heat_index,
            sort_order="desc",
        )

    async def get_categories(self) -> list[str]:
        """获取所有唯一分类

        Returns:
            分类列表
        """
        query = (
            select(Theme.category)
            .where(
                Theme.deleted_at.is_(None),
                exclude_market_signals(),
                Theme.category.isnot(None),
            )
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
            .where(Theme.deleted_at.is_(None), exclude_market_signals())
            .order_by(desc(Theme.heat_index))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_market_signals(self) -> list[Theme]:
        """获取独立展示的市场表现板块。"""
        query = (
            select(Theme)
            .where(Theme.deleted_at.is_(None), only_market_signals())
            .order_by(desc(Theme.rise_fall_pct), desc(Theme.heat_index))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_indicator_signals(self) -> list[Theme]:
        """获取独立展示的行情指标板块（新高、财报预告、破增发等）。"""
        query = (
            select(Theme)
            .where(Theme.deleted_at.is_(None), only_indicator_signals())
            .order_by(desc(Theme.rise_fall_pct), desc(Theme.heat_index))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def stream_all(
        self,
        category: str | None = None,
        chunk_size: int = 200,
    ):
        """流式获取所有题材（用于导出，避免一次性加载全部数据）

        使用 yield_per 实现服务端游标分批读取，内存占用 O(chunk_size) 而非 O(N)。

        Args:
            category: 分类筛选
            chunk_size: 每批读取数量

        Yields:
            单个题材对象
        """
        query = (
            select(Theme)
            .where(Theme.deleted_at.is_(None), exclude_market_signals())
            .order_by(Theme.id)
        )

        if category:
            query = query.where(Theme.category == category)

        # 使用 yield_per 开启服务端游标，分批读取
        stream = await self.session.stream(
            query.execution_options(yield_per=chunk_size)
        )
        async for result in stream:
            yield result.scalar_one()

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

    async def count_stocks_by_chain_level(self, theme_id: int) -> dict[str, int]:
        """统计题材各产业链层级的成分股数量。"""
        query = (
            select(ThemeStock.chain_level, func.count(ThemeStock.stock_id))
            .where(
                ThemeStock.theme_id == theme_id,
                ThemeStock.chain_level.in_(("upstream", "midstream", "downstream")),
            )
            .group_by(ThemeStock.chain_level)
        )
        result = await self.session.execute(query)
        counts = {"upstream": 0, "midstream": 0, "downstream": 0}
        counts.update({level: count for level, count in result.all()})
        return counts

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

        return await self._paginate(
            query=base_query,
            page=page,
            page_size=page_size,
            sort_column=ThemeStock.sort_order,
            sort_order="asc",
        )

    async def list_with_stock_quotes(self) -> list[Theme]:
        """一次加载全部有效题材及其成分股最新行情。"""
        query = (
            select(Theme)
            .where(Theme.deleted_at.is_(None), exclude_market_signals())
            .options(selectinload(Theme.stocks).selectinload(ThemeStock.stock))
            .order_by(Theme.id)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
