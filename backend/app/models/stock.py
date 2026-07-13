"""股票模型

定义股票表结构。
"""

from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Stock(Base, TimestampMixin):
    """股票表模型"""

    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, comment="股票代码")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="股票名称")
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="所属行业")
    market_cap: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(20, 2), nullable=True, comment="总市值"
    )
    current_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True, comment="当前价格"
    )
    rise_fall_pct: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 4), nullable=True, comment="涨跌幅(%)"
    )
    exchange: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="交易所(SH/SZ/BJ)")

    # 关系定义
    themes: Mapped[list["ThemeStock"]] = relationship(back_populates="stock", cascade="all, delete-orphan")
    events: Mapped[list["Event"]] = relationship(back_populates="stock")

    # 表级配置：索引
    # 注意：code 字段有 UNIQUE 约束，PostgreSQL 会自动创建索引，无需额外定义
    __table_args__ = (
        Index("idx_stock_name", "name"),
        {"comment": "股票表"},
    )

    def __repr__(self) -> str:
        return f"<Stock(id={self.id}, code='{self.code}', name='{self.name}')>"
