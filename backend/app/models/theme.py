"""题材模型

定义题材表结构，支持软删除。
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Index, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import Base, TimestampMixin


class Theme(Base, TimestampMixin):
    """题材表模型"""

    __tablename__ = "themes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="题材名称")
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="题材代码")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="题材描述")
    heat_index: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=0, server_default="0", comment="热度指数"
    )
    rise_fall_pct: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), nullable=False, default=0, server_default="0", comment="涨跌幅(%)"
    )
    stock_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="关联股票数量"
    )
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="题材分类")
    tags: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, comment="标签列表")
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="数据来源")

    # 软删除字段
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="软删除时间"
    )

    # 关系定义
    stocks: Mapped[list["ThemeStock"]] = relationship(back_populates="theme", cascade="all, delete-orphan")
    industry_chains: Mapped[list["IndustryChain"]] = relationship(back_populates="theme", cascade="all, delete-orphan")

    # 表级配置：索引
    __table_args__ = (
        Index("idx_theme_name", "name"),
        Index("idx_theme_heat_index", "heat_index"),
        Index("idx_theme_category", "category"),
        {"comment": "题材表"},
    )

    @property
    def is_deleted(self) -> bool:
        """检查是否已删除"""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """软删除：设置 deleted_at"""
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self) -> None:
        """恢复：清除 deleted_at"""
        self.deleted_at = None

    def __repr__(self) -> str:
        return f"<Theme(id={self.id}, name='{self.name}', code='{self.code}')>"
