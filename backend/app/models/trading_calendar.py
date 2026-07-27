"""A 股交易日历 ORM 模型。"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TradingCalendarDay(Base):
    """开市日（仅存开市，不在表中视为休市）。"""

    __tablename__ = "trading_calendar_days"

    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="akshare_sina")
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class TradingCalendarMeta(Base):
    """交易日历同步元信息（单行 id=1）。"""

    __tablename__ = "trading_calendar_meta"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="akshare_sina")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    min_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    max_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
