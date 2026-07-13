"""股票和事件仓储

提供 Stock 和 Event 的数据库查询操作。
"""

from sqlalchemy import desc, asc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.stock import Stock
from app.models.event import Event


# 允许排序的字段白名单
STOCK_SORT_FIELDS = {
    "code", "name", "industry", "market_cap", "current_price", "rise_fall_pct",
}
EVENT_SORT_FIELDS = {"title", "event_type", "published_at"}


class StockRepository:
    """股票仓储"""

    def __init__(self, session: AsyncSession):
        self.session = session

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

        # 计算总数
        count_query = select(func.count()).select_from(base_query.subquery())
        total = (await self.session.execute(count_query)).scalar() or 0

        # 应用排序（白名单验证）
        sort_column = getattr(Stock, sort_by, None)
        if sort_column is None or sort_by not in STOCK_SORT_FIELDS:
            sort_column = Stock.code
        if order == "desc":
            base_query = base_query.order_by(desc(sort_column))
        else:
            base_query = base_query.order_by(asc(sort_column))

        # 应用分页
        offset = (page - 1) * page_size
        base_query = base_query.offset(offset).limit(page_size)

        result = await self.session.execute(base_query)
        stocks = list(result.scalars().all())

        return stocks, total

    async def get_by_code(self, code: str) -> Stock | None:
        """获取股票详情（含最近事件）

        Args:
            code: 股票代码

        Returns:
            股票对象或 None
        """
        query = (
            select(Stock)
            .where(Stock.code == code)
            .options(selectinload(Stock.events))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

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

        # 计算总数
        count_query = select(func.count()).select_from(base_query.subquery())
        total = (await self.session.execute(count_query)).scalar() or 0

        # 按 published_at 降序排序
        base_query = base_query.order_by(desc(Event.published_at))

        # 应用分页
        offset = (page - 1) * page_size
        base_query = base_query.offset(offset).limit(page_size)

        result = await self.session.execute(base_query)
        events = list(result.scalars().all())

        return events, total


class EventRepository:
    """事件仓储"""

    def __init__(self, session: AsyncSession):
        self.session = session

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

        # 计算总数
        count_query = select(func.count()).select_from(base_query.subquery())
        total = (await self.session.execute(count_query)).scalar() or 0

        # 应用排序（白名单验证）
        sort_column = getattr(Event, sort_by, None)
        if sort_column is None or sort_by not in EVENT_SORT_FIELDS:
            sort_column = Event.published_at
        if order == "desc":
            base_query = base_query.order_by(desc(sort_column))
        else:
            base_query = base_query.order_by(asc(sort_column))

        # 应用分页
        offset = (page - 1) * page_size
        base_query = base_query.offset(offset).limit(page_size)

        result = await self.session.execute(base_query)
        events = list(result.scalars().all())

        return events, total
