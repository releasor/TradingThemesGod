"""可递归下钻的概念节点模型。"""

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    BigInteger,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.concept_node_stock import ConceptNodeStock
    from app.models.theme import Theme


class ConceptNode(Base, TimestampMixin):
    """题材知识图谱节点，使用 parent_id 支持任意深度。"""

    __tablename__ = "concept_nodes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    theme_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("themes.id", ondelete="CASCADE"), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("concept_nodes.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    path_key: Mapped[str] = mapped_column(String(500), nullable=False)
    node_type: Mapped[str] = mapped_column(String(30), nullable=False, default="segment", server_default="segment")
    description: Mapped[str | None] = mapped_column(Text)
    chain_level: Mapped[str | None] = mapped_column(String(20))
    market_logic: Mapped[str | None] = mapped_column(Text)
    catalysts: Mapped[list | dict] = mapped_column(JSON, nullable=False, default=list)
    risks: Mapped[list | dict] = mapped_column(JSON, nullable=False, default=list)
    sources: Mapped[list | dict] = mapped_column(JSON, nullable=False, default=list)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False, default=0, server_default="0")
    depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    theme: Mapped["Theme"] = relationship(back_populates="concept_nodes")
    parent: Mapped["ConceptNode | None"] = relationship(remote_side=[id], back_populates="children")
    children: Mapped[list["ConceptNode"]] = relationship(back_populates="parent", cascade="all, delete-orphan")
    stock_links: Mapped[list["ConceptNodeStock"]] = relationship(back_populates="node", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_concept_node_theme_parent", "theme_id", "parent_id"),
        Index("idx_concept_node_theme_path", "theme_id", "path_key", unique=True),
        {"comment": "题材递归概念节点"},
    )
