"""题材挖掘 ORM 模型。"""

from datetime import date
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ThemeMiningCard(Base):
    """题材挖掘日快照卡。"""

    __tablename__ = "theme_mining_cards"
    __table_args__ = (
        UniqueConstraint(
            "trade_date",
            "theme_id",
            "mining_type",
            name="uq_theme_mining_cards_date_theme_type",
        ),
        Index(
            "idx_theme_mining_cards_date_type_rank",
            "trade_date",
            "mining_type",
            "rank",
        ),
        {"comment": "题材挖掘日快照卡"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    theme_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("themes.id", ondelete="CASCADE"),
        nullable=False,
    )
    mining_type: Mapped[str] = mapped_column(String(32), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rank: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lifecycle_stage: Mapped[str] = mapped_column(String(32), nullable=False)
    strength_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rationale: Mapped[str] = mapped_column(Text, nullable=False, default="")
    score_breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    degraded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    missing_metrics: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)


class ThemeMiningMember(Base):
    """题材挖掘卡成份股明细。"""

    __tablename__ = "theme_mining_members"
    __table_args__ = (
        UniqueConstraint(
            "card_id",
            "stock_id",
            name="uq_theme_mining_members_card_stock",
        ),
        Index("idx_theme_mining_members_card_rank", "card_id", "rank"),
        {"comment": "题材挖掘卡成份股明细"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    card_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("theme_mining_cards.id", ondelete="CASCADE"),
        nullable=False,
    )
    stock_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("stocks.id", ondelete="CASCADE"),
        nullable=False,
    )
    concept_node_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("concept_nodes.id", ondelete="SET NULL"),
        nullable=True,
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rank: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    role_tag: Mapped[str] = mapped_column(String(32), nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class ThemeMiningNote(Base, TimestampMixin):
    """题材挖掘卡用户模型点评。"""

    __tablename__ = "theme_mining_notes"
    __table_args__ = (
        UniqueConstraint(
            "card_id",
            "user_id",
            name="uq_theme_mining_notes_card_user",
        ),
        {"comment": "题材挖掘卡用户模型点评"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    card_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("theme_mining_cards.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    content_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    model_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
