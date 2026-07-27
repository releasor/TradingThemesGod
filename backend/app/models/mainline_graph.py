"""主线图谱 ORM 模型。"""

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class MainlineGraphVersion(Base, TimestampMixin):
    """主线图谱版本：auto / draft / published。"""

    __tablename__ = "mainline_graph_versions"
    __table_args__ = (
        Index(
            "idx_mainline_graph_versions_date_kind_status",
            "trade_date",
            "kind",
            "status",
        ),
        {"comment": "主线图谱版本"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    parent_version_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("mainline_graph_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class MainlineGraphNode(Base):
    """主线图谱节点：题材快照。"""

    __tablename__ = "mainline_graph_nodes"
    __table_args__ = (
        UniqueConstraint(
            "version_id",
            "theme_id",
            name="uq_mainline_graph_nodes_version_theme",
        ),
        {"comment": "主线图谱节点"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    version_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("mainline_graph_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    theme_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("themes.id", ondelete="CASCADE"),
        nullable=False,
    )
    mainline_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    strength_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lifecycle_stage: Mapped[str] = mapped_column(String(32), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class MainlineGraphEdge(Base):
    """主线图谱边：主线→支线关系。"""

    __tablename__ = "mainline_graph_edges"
    __table_args__ = (
        UniqueConstraint(
            "version_id",
            "from_theme_id",
            "to_theme_id",
            name="uq_mainline_graph_edges_version_from_to",
        ),
        {"comment": "主线图谱边"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    version_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("mainline_graph_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_theme_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("themes.id", ondelete="CASCADE"),
        nullable=False,
    )
    to_theme_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("themes.id", ondelete="CASCADE"),
        nullable=False,
    )
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    method: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
