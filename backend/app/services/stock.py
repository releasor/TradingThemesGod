"""股票和事件服务

提供股票和事件相关的业务逻辑。
"""

from math import ceil
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.stock import StockRepository, EventRepository
from app.schemas.stock import (
    StockBrief,
    StockDetailResponse,
    StockListResponse,
    EventBrief,
    EventListResponse,
)


class StockService:
    """股票服务"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.stock_repo = StockRepository(session)
        self.event_repo = EventRepository(session)

    async def list_stocks(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "code",
        order: str = "asc",
        industry: str | None = None,
        exchange: str | None = None,
    ) -> StockListResponse:
        """获取股票列表（分页）

        Args:
            page: 页码
            page_size: 每页数量
            sort_by: 排序字段
            order: 排序方向
            industry: 按行业筛选
            exchange: 按交易所筛选

        Returns:
            分页股票列表
        """
        stocks, total = await self.stock_repo.list_paginated(
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            order=order,
            industry=industry,
            exchange=exchange,
        )

        return StockListResponse(
            items=[StockBrief.model_validate(s) for s in stocks],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=ceil(total / page_size) if total > 0 else 0,
        )

    async def get_stock_detail(self, code: str) -> StockDetailResponse:
        """获取股票详情（含最近5条事件）

        Args:
            code: 股票代码

        Returns:
            股票详情

        Raises:
            HTTPException: 股票不存在
        """
        stock = await self.stock_repo.get_by_code(code)
        if stock is None:
            raise HTTPException(status_code=404, detail="股票不存在")

        # 取最近5条事件，按 published_at 降序
        recent_events = sorted(
            stock.events,
            key=lambda e: e.published_at or e.created_at,
            reverse=True,
        )[:5]

        return StockDetailResponse(
            id=stock.id,
            code=stock.code,
            name=stock.name,
            industry=stock.industry,
            market_cap=stock.market_cap,
            current_price=stock.current_price,
            rise_fall_pct=stock.rise_fall_pct,
            exchange=stock.exchange,
            created_at=stock.created_at,
            updated_at=stock.updated_at,
            recent_events=[EventBrief.model_validate(e) for e in recent_events],
        )

    async def get_stock_events(
        self,
        code: str,
        page: int = 1,
        page_size: int = 20,
    ) -> EventListResponse:
        """获取股票的事件列表（分页，按 published_at 降序）

        Args:
            code: 股票代码
            page: 页码
            page_size: 每页数量

        Returns:
            分页事件列表

        Raises:
            HTTPException: 股票不存在
        """
        events, total = await self.stock_repo.get_events_by_code(
            code=code,
            page=page,
            page_size=page_size,
        )

        # 如果股票不存在（返回空列表且总数为0），检查股票是否存在
        if total == 0:
            stock = await self.stock_repo.get_by_code(code)
            if stock is None:
                raise HTTPException(status_code=404, detail="股票不存在")

        return EventListResponse(
            items=[EventBrief.model_validate(e) for e in events],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=ceil(total / page_size) if total > 0 else 0,
        )

    async def list_events(
        self,
        page: int = 1,
        page_size: int = 20,
        event_type: str | None = None,
        sort_by: str = "published_at",
        order: str = "desc",
    ) -> EventListResponse:
        """获取事件列表（分页）

        Args:
            page: 页码
            page_size: 每页数量
            event_type: 按事件类型筛选
            sort_by: 排序字段
            order: 排序方向

        Returns:
            分页事件列表
        """
        events, total = await self.event_repo.list_paginated(
            page=page,
            page_size=page_size,
            event_type=event_type,
            sort_by=sort_by,
            order=order,
        )

        return EventListResponse(
            items=[EventBrief.model_validate(e) for e in events],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=ceil(total / page_size) if total > 0 else 0,
        )
