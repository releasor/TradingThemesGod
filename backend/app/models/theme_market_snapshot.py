"""题材每日市场快照模型。"""

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.theme import Theme


class ThemeMarketSnapshot(Base, TimestampMixin):
    """题材成分股在单个交易日的市场广度统计。"""

    __tablename__ = "theme_market_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    theme_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("themes.id", ondelete="CASCADE"),
        nullable=False,
    )
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    up_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    down_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    flat_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    suspended_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    limit_up_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    limit_down_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    theme: Mapped["Theme"] = relationship(back_populates="market_snapshots")

    __table_args__ = (
        Index(
            "idx_theme_market_snapshots_theme_date",
            "theme_id",
            "trade_date",
            unique=True,
        ),
        {"comment": "题材每日市场快照"},
    )
