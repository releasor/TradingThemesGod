"""复盘台事件溯源 ORM 模型。"""

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ReviewRun(Base, TimestampMixin):
    """复盘运行外壳：记录一次 refresh/analyze 等任务。"""

    __tablename__ = "review_runs"
    __table_args__ = (
        Index("idx_review_runs_date_started", "trade_date", "started_at"),
        Index("idx_review_runs_type_date", "run_type", "trade_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    run_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)  # running|success|partial|failed
    source_status: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    request_meta: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReviewEvent(Base, TimestampMixin):
    """复盘实体事件：策略卡、候选、阶段迁移等。"""

    __tablename__ = "review_events"
    __table_args__ = (
        Index("idx_review_events_date_type", "trade_date", "event_type"),
        Index("idx_review_events_run", "run_id"),
        Index("idx_review_events_entity", "entity_type", "entity_id", "trade_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("review_runs.id", ondelete="CASCADE"), nullable=True
    )
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReviewAiReport(Base, TimestampMixin):
    """复盘 AI 题材日报或规则摘要。"""

    __tablename__ = "review_ai_reports"
    __table_args__ = (
        UniqueConstraint("trade_date", "user_id", name="uq_review_ai_reports_date_user"),
        Index("ix_review_ai_reports_trade_date", "trade_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    content_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    content_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    model_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_run_ids: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
