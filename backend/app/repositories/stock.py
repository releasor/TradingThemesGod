"""股票和事件仓储

提供 Stock 和 Event 的数据库查询操作。
"""

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock import Stock
from app.models.event import Event
from app.repositories.base import BaseRepository


# 允许排序的字段白名单
STOCK_SORT_FIELDS = {
    "code", "name", "industry", "market_cap", "current_price", "rise_fall_pct",
}
EVENT_SORT_FIELDS = {"title", "event_type", "published_at"}


class StockRepository(BaseRepository):
    """股票仓储"""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def list_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "code",
        order: str = "asc",
        industry: str | None = None,
        exchange: str | None = None,
    ) -> tuple[list[Stock], int]:
        """分页查询股票列表

        Args:
            page: 页码
            page_size: 每页数量
            sort_by: 排序字段
            order: 排序方向
            industry: 按行业筛选
            exchange: 按交易所筛选

        Returns:
            (股票列表, 总数)
        """
        base_query = select(Stock)

        # 应用筛选
        if industry:
            base_query = base_query.where(Stock.industry == industry)
        if exchange:
            base_query = base_query.where(Stock.exchange == exchange)

        # 确定排序列
        sort_column = getattr(Stock, sort_by, None)
        if sort_column is None or sort_by not in STOCK_SORT_FIELDS:
            sort_column = Stock.code

        return await self._paginate(
            query=base_query,
            page=page,
            page_size=page_size,
            sort_column=sort_column,
            sort_order=order,
        )

    async def get_by_code(self, code: str) -> Stock | None:
        """获取股票详情

        Args:
            code: 股票代码

        Returns:
            股票对象或 None
        """
        query = select(Stock).where(Stock.code == code)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def exists_by_code(self, code: str) -> bool:
        """检查股票是否存在（轻量级，不加载关联数据）

        Args:
            code: 股票代码

        Returns:
            是否存在
        """
        query = select(Stock.id).where(Stock.code == code).limit(1)
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def get_events_by_code(
        self,
        code: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Event], int]:
        """获取股票的事件列表（分页，按 published_at 降序）

        Args:
            code: 股票代码
            page: 页码
            page_size: 每页数量

        Returns:
            (事件列表, 总数)
        """
        # 先查找股票
        stock_query = select(Stock.id).where(Stock.code == code)
        stock_result = await self.session.execute(stock_query)
        stock_id = stock_result.scalar_one_or_none()
        if stock_id is None:
            return [], 0

        base_query = select(Event).where(Event.stock_id == stock_id)

        return await self._paginate(
            query=base_query,
            page=page,
            page_size=page_size,
            sort_column=Event.published_at,
            sort_order="desc",
        )


class EventRepository(BaseRepository):
    """事件仓储"""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_recent_by_stock_id(self, stock_id: int, limit: int = 5) -> list[Event]:
        """获取指定股票的最近事件（按 published_at 降序）

        Args:
            stock_id: 股票ID
            limit: 返回数量

        Returns:
            事件列表
        """
        query = (
            select(Event)
            .where(Event.stock_id == stock_id)
            .order_by(desc(Event.published_at))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        event_type: str | None = None,
        sort_by: str = "published_at",
        order: str = "desc",
    ) -> tuple[list[Event], int]:
        """分页查询事件列表

        Args:
            page: 页码
            page_size: 每页数量
            event_type: 按事件类型筛选
            sort_by: 排序字段
            order: 排序方向

        Returns:
            (事件列表, 总数)
        """
        base_query = select(Event)

        # 应用筛选
        if event_type:
            base_query = base_query.where(Event.event_type == event_type)

        # 确定排序列
        sort_column = getattr(Event, sort_by, None)
        if sort_column is None or sort_by not in EVENT_SORT_FIELDS:
            sort_column = Event.published_at

        return await self._paginate(
            query=base_query,
            page=page,
            page_size=page_size,
            sort_column=sort_column,
            sort_order=order,
        )
