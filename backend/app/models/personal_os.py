"""个人 AI OS ORM 模型。"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class OsProfile(Base, TimestampMixin):
    __tablename__ = "os_profiles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    goals: Mapped[str | None] = mapped_column(Text, nullable=True)
    health_baseline: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    memory_policy: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    module_flags: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    model_prefs: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    report_prompt_appendix: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_prompt_appendix: Mapped[str | None] = mapped_column(Text, nullable=True)


class OsNote(Base, TimestampMixin):
    __tablename__ = "os_notes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


class OsChatSession(Base, TimestampMixin):
    __tablename__ = "os_chat_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    provider_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


class OsChatMessage(Base):
    __tablename__ = "os_chat_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("os_chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    provider_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class OsJournalEntry(Base, TimestampMixin):
    __tablename__ = "os_journal_entries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


class OsDailyReport(Base, TimestampMixin):
    __tablename__ = "os_daily_reports"
    __table_args__ = (
        UniqueConstraint("user_id", "report_date", name="uq_os_daily_reports_user_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    provider_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    entry_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    feedback_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    feedback_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class OsDecisionThread(Base, TimestampMixin):
    __tablename__ = "os_decision_threads"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    constraints: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="open")
    chosen_option_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    outcome_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class OsDecisionRun(Base, TimestampMixin):
    __tablename__ = "os_decision_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    thread_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("os_decision_threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


class OsDashboardPin(Base, TimestampMixin):
    """用户钉到仪表盘的跨模块条目。"""

    __tablename__ = "os_dashboard_pins"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "source_type",
            "source_id",
            name="uq_os_dashboard_pins_user_source",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class OsDecisionOption(Base):
    __tablename__ = "os_decision_options"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("os_decision_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tier: Mapped[str] = mapped_column(String(20), nullable=False)  # upper|mid|lower
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    provider_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    raw_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    feedback_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    feedback_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
