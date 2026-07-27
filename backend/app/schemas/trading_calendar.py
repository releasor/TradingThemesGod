"""交易日历 API DTO。"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class TradingCalendarStatus(BaseModel):
    source: str = "akshare_sina"
    last_synced_at: datetime | None = None
    row_count: int = 0
    min_date: date | None = None
    max_date: date | None = None
    last_error: str | None = None
    degraded: bool = True
    today_is_trade_day: bool = False
    data_trade_date: date
    missing_sources: list[str] = Field(default_factory=list)


class TradingCalendarResolve(BaseModel):
    input_date: date
    trade_date: date
