"""题材-股票关联表

定义题材和股票的多对多关联关系。
"""

from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, PrimaryKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ThemeStock(Base, TimestampMixin):
    """题材-股票关联表模型"""

    __tablename__ = "theme_stocks"

    theme_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("themes.id", ondelete="CASCADE"), nullable=False, comment="题材ID"
    )
    stock_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, comment="股票ID"
    )
    chain_level: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="产业链层级"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="排序顺序"
    )

    # 关系定义
    theme: Mapped["Theme"] = relationship(back_populates="stocks")
    stock: Mapped["Stock"] = relationship(back_populates="themes")

    # 复合主键和索引
    __table_args__ = (
        PrimaryKeyConstraint("theme_id", "stock_id", name="pk_theme_stocks"),
        Index("idx_theme_stocks_stock_id", "stock_id"),
        {"comment": "题材-股票关联表"},
    )

    def __repr__(self) -> str:
        return f"<ThemeStock(theme_id={self.theme_id}, stock_id={self.stock_id})>"
