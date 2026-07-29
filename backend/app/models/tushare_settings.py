"""Tushare 数据源全局配置（单例 id=1）。"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TushareSettings(Base):
    """Tushare 启用状态与加密 Token（全站共享）。"""

    __tablename__ = "tushare_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
