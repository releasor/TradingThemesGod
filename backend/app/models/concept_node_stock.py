"""概念节点与股票的有依据关联。"""

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    ForeignKey,
    Index,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.concept_node import ConceptNode
    from app.models.stock import Stock


class ConceptNodeStock(Base, TimestampMixin):
    __tablename__ = "concept_node_stocks"

    node_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("concept_nodes.id", ondelete="CASCADE"), nullable=False)
    stock_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    relevance_score: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False, default=0, server_default="0")
    is_core: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    sources: Mapped[list | dict] = mapped_column(JSON, nullable=False, default=list)

    node: Mapped["ConceptNode"] = relationship(back_populates="stock_links")
    stock: Mapped["Stock"] = relationship(back_populates="concept_node_links")

    __table_args__ = (
        PrimaryKeyConstraint("node_id", "stock_id", name="pk_concept_node_stocks"),
        Index("idx_concept_node_stock_stock_id", "stock_id"),
        {"comment": "概念节点股票关联"},
    )
