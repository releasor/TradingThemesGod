"""短线雷达相关 ORM 模型。"""

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class DailyStockSignal(Base, TimestampMixin):
    """每日个股短线信号。"""

    __tablename__ = "daily_stock_signals"
    __table_args__ = (
        UniqueConstraint(
            "trade_date",
            "stock_id",
            "signal_type",
            name="uq_daily_stock_signals_date_stock_type",
        ),
        Index("idx_daily_stock_signals_date_type", "trade_date", "signal_type"),
        Index("idx_daily_stock_signals_date_stock", "trade_date", "stock_id"),
        Index("idx_daily_stock_signals_date_theme", "trade_date", "theme_id"),
        {"comment": "每日个股短线信号"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    stock_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False
    )
    theme_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("themes.id", ondelete="SET NULL"), nullable=True
    )
    signal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    limit_up_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    first_limit_up_at: Mapped[time | None] = mapped_column(Time, nullable=True)
    last_limit_up_at: Mapped[time | None] = mapped_column(Time, nullable=True)
    open_board_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    streak_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_one_word: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_failed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    turnover_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    market_cap: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    float_market_cap: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    source_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class DragonTigerEntry(Base, TimestampMixin):
    """龙虎榜明细。"""

    __tablename__ = "dragon_tiger_entries"
    __table_args__ = (
        UniqueConstraint(
            "trade_date",
            "stock_id",
            "reason",
            name="uq_dragon_tiger_entries_date_stock_reason",
        ),
        Index("idx_dragon_tiger_entries_date_stock", "trade_date", "stock_id"),
        Index("idx_dragon_tiger_entries_date_net", "trade_date", "net_amount"),
        {"comment": "龙虎榜明细"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    stock_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False
    )
    reason: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    buy_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    sell_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    net_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    seat_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    source_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class SectorRotationSnapshot(Base, TimestampMixin):
    """题材日轮动快照（含生命周期与四维强度）。"""

    __tablename__ = "sector_rotation_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "trade_date",
            "theme_id",
            name="uq_sector_rotation_snapshots_date_theme",
        ),
        Index("idx_sector_rotation_snapshots_date_theme", "trade_date", "theme_id"),
        Index("idx_sector_rotation_snapshots_date_mainline", "trade_date", "mainline_score"),
        {"comment": "题材日轮动与生命周期快照"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    theme_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("themes.id", ondelete="CASCADE"), nullable=False
    )
    trend_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    emotion_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rotation_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mainline_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    strong_stock_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    limit_up_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_limit_up_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    near_limit_up_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latest_catalyst_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="rules")
    lifecycle_stage: Mapped[str] = mapped_column(String(32), nullable=False)
    lifecycle_confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    strength_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    limit_quality_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    flow_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    leader_clarity_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    breadth_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    degraded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    missing_metrics: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)


class ShortTermSignalRun(Base, TimestampMixin):
    """短线信号刷新运行记录。"""

    __tablename__ = "short_term_signal_runs"
    __table_args__ = (
        Index("idx_short_term_signal_runs_date_status", "trade_date", "status"),
        {"comment": "短线信号刷新运行记录"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_status: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class ShortTermCandidate(Base, TimestampMixin):
    """短线规则候选结果。"""

    __tablename__ = "short_term_candidates"
    __table_args__ = (
        UniqueConstraint(
            "trade_date",
            "strategy",
            "stock_id",
            name="uq_short_term_candidates_date_strategy_stock",
        ),
        Index(
            "idx_short_term_candidates_date_strategy_rank",
            "trade_date",
            "strategy",
            "rank",
        ),
        Index("idx_short_term_candidates_date_stock", "trade_date", "stock_id"),
        Index("idx_short_term_candidates_date_theme", "trade_date", "theme_id"),
        {"comment": "短线规则候选结果"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    strategy: Mapped[str] = mapped_column(String(64), nullable=False)
    stock_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False
    )
    theme_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("themes.id", ondelete="SET NULL"), nullable=True
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rank: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    matched_rules: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    excluded_rules: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    risk_flags: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    outlook: Mapped[str] = mapped_column(Text, nullable=False, default="")
    operation_advice: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tracking_focus: Mapped[str] = mapped_column(Text, nullable=False, default="")
    core_conclusion: Mapped[str] = mapped_column(Text, nullable=False, default="")
