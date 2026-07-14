"""股票和事件相关 Pydantic 模型

定义股票和事件 API 的请求和响应数据结构。
"""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class StockBrief(BaseModel):
    """股票简要信息（列表用）"""

    id: int = Field(description="股票ID")
    code: str = Field(description="股票代码")
    name: str = Field(description="股票名称")
    industry: str | None = Field(default=None, description="所属行业")
    market_cap: Decimal | None = Field(default=None, description="总市值")
    current_price: Decimal | None = Field(default=None, description="当前价格")
    rise_fall_pct: Decimal | None = Field(default=None, description="涨跌幅(%)")
    exchange: str | None = Field(default=None, description="交易所(SH/SZ/BJ)")

    model_config = {"from_attributes": True}


class EventBrief(BaseModel):
    """事件简要信息"""

    id: int = Field(description="事件ID")
    title: str = Field(description="事件标题")
    content: str | None = Field(default=None, description="事件内容")
    source: str | None = Field(default=None, description="信息来源")
    event_type: str | None = Field(default=None, description="事件类型")
    published_at: datetime | None = Field(default=None, description="发布时间")

    model_config = {"from_attributes": True}


class EventListItem(BaseModel):
    """事件列表项（不含content，减少列表响应体积）"""

    id: int = Field(description="事件ID")
    title: str = Field(description="事件标题")
    source: str | None = Field(default=None, description="信息来源")
    event_type: str | None = Field(default=None, description="事件类型")
    published_at: datetime | None = Field(default=None, description="发布时间")

    model_config = {"from_attributes": True}


class StockListResponse(BaseModel):
    """股票列表响应"""

    items: list[StockBrief] = Field(description="股票列表")
    total: int = Field(description="总数")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页数量")
    total_pages: int = Field(description="总页数")


class StockDetailResponse(BaseModel):
    """股票详情响应"""

    id: int = Field(description="股票ID")
    code: str = Field(description="股票代码")
    name: str = Field(description="股票名称")
    industry: str | None = Field(default=None, description="所属行业")
    market_cap: Decimal | None = Field(default=None, description="总市值")
    current_price: Decimal | None = Field(default=None, description="当前价格")
    rise_fall_pct: Decimal | None = Field(default=None, description="涨跌幅(%)")
    exchange: str | None = Field(default=None, description="交易所(SH/SZ/BJ)")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")
    recent_events: list[EventListItem] = Field(description="最近事件（最多5条）")

    model_config = {"from_attributes": True}

    @field_validator('code')
    @classmethod
    def validate_stock_code(cls, v: str) -> str:
        """验证股票代码格式"""
        if not v.isdigit() or len(v) != 6:
            raise ValueError('股票代码必须是6位数字')
        return v


class EventListResponse(BaseModel):
    """事件列表响应"""

    items: list[EventListItem] = Field(description="事件列表")
    total: int = Field(description="总数")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页数量")
    total_pages: int = Field(description="总页数")


__all__ = [
    "StockBrief",
    "EventBrief",
    "EventListItem",
    "StockListResponse",
    "StockDetailResponse",
    "EventListResponse",
]
