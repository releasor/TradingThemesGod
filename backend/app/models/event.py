"""事件模型

定义事件表结构。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Event(Base, TimestampMixin):
    """事件表模型"""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="事件标题")
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="事件内容")
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="信息来源")
    event_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="事件类型")
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="发布时间"
    )
    stock_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("stocks.id", ondelete="SET NULL"), nullable=True, comment="关联股票ID"
    )

    # 关系定义
    stock: Mapped[Optional["Stock"]] = relationship(back_populates="events")

    # 表级配置：索引
    __table_args__ = (
        Index("idx_event_stock_id", "stock_id"),
        Index("idx_event_published_at", "published_at"),
        {"comment": "事件表"},
    )

    def __repr__(self) -> str:
        return f"<Event(id={self.id}, title='{self.title[:30]}...')>"
