"""个股 AI 研判报告持久化模型。"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class StockAiReport(Base, TimestampMixin):
    """每用户每股票最近一份 AI 买入/持有研判报告。"""

    __tablename__ = "stock_ai_reports"
    __table_args__ = (
        UniqueConstraint("user_id", "stock_code", name="uq_stock_ai_reports_user_code"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stock_code: Mapped[str] = mapped_column(String(6), nullable=False, index=True)
    stock_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    verdict: Mapped[str] = mapped_column(String(16), nullable=False)
    horizon_short: Mapped[str] = mapped_column(Text, nullable=False)
    horizon_swing: Mapped[str] = mapped_column(Text, nullable=False)
    horizon_medium_long: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    sections: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    full_report: Mapped[str] = mapped_column(Text, nullable=False)
    context_digest: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    model_provider_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    elapsed_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
