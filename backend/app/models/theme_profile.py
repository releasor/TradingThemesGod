"""题材结构化档案模型。"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.theme import Theme


class ThemeProfile(Base, TimestampMixin):
    """题材的一对一结构化详细介绍。"""

    __tablename__ = "theme_profiles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    theme_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("themes.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    core_logic: Mapped[str] = mapped_column(Text, nullable=False)
    applications: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    catalysts: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    risks: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    sources: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    theme: Mapped["Theme"] = relationship(back_populates="profile")
