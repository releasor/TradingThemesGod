"""催化雷达分类审计 ORM 模型。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CatalystClassification(Base):
    """驱动事件分类审计快照。"""

    __tablename__ = "catalyst_classifications"
    __table_args__ = (
        Index(
            "idx_catalyst_classifications_event_created",
            "event_id",
            "created_at",
        ),
        {"comment": "催化分类审计快照"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("theme_driver_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    freshness: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
