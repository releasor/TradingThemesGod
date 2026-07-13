"""产业链模型

定义产业链表结构。
"""

from typing import Optional

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import Base, TimestampMixin


class IndustryChain(Base, TimestampMixin):
    """产业链表模型"""

    __tablename__ = "industry_chains"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    theme_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("themes.id", ondelete="CASCADE"), nullable=False, comment="关联题材ID"
    )
    level: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="产业链层级(upstream/midstream/downstream)"
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="环节名称")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="环节描述")
    representative_companies: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="代表公司列表"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="排序顺序"
    )

    # 关系定义
    theme: Mapped["Theme"] = relationship(back_populates="industry_chains")

    # 表级配置：索引和约束
    __table_args__ = (
        Index("idx_industry_chain_theme_id", "theme_id"),
        CheckConstraint(
            "level IN ('upstream', 'midstream', 'downstream')",
            name="ck_industry_chain_level"
        ),
        {"comment": "产业链表"},
    )

    def __repr__(self) -> str:
        return f"<IndustryChain(id={self.id}, name='{self.name}', level='{self.level}')>"
