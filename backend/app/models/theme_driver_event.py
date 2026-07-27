"""题材驱动事件模型。"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.theme import Theme


class ThemeDriverEvent(Base, TimestampMixin):
    """经筛选并可追溯来源的题材驱动事件。"""

    __tablename__ = "theme_driver_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    theme_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("themes.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    url_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    event_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    relevance_score: Mapped[int] = mapped_column(Integer, nullable=False)
    crawled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    freshness: Mapped[str] = mapped_column(
        String(16), nullable=False, default="unknown"
    )
    actor_type: Mapped[str] = mapped_column(
        String(16), nullable=False, default="unknown"
    )
    classified_by: Mapped[str | None] = mapped_column(String(16), nullable=True)
    classified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    theme: Mapped["Theme"] = relationship(back_populates="driver_events")

    __table_args__ = (
        Index(
            "idx_theme_driver_events_theme_url",
            "theme_id",
            "url_hash",
            unique=True,
        ),
        Index(
            "idx_theme_driver_events_theme_event",
            "theme_id",
            "event_key",
            unique=True,
        ),
        Index("idx_theme_driver_events_theme_id", "theme_id"),
        Index("idx_theme_driver_events_published_at", "published_at"),
        Index("idx_theme_driver_events_theme_published", "theme_id", "published_at"),
        Index(
            "idx_theme_driver_events_freshness_published",
            "freshness",
            "published_at",
        ),
        Index(
            "idx_theme_driver_events_actor_published",
            "actor_type",
            "published_at",
        ),
        {"comment": "题材驱动事件"},
    )
