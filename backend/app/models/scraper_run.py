"""爬虫运行记录模型

记录每次爬虫运行的状态、结果和错误信息。
"""

from datetime import datetime
from sqlalchemy import BigInteger, String, Integer, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class ScraperRun(Base, TimestampMixin):
    """爬虫运行记录"""

    __tablename__ = "scraper_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="running"
    )  # running / completed / failed
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    items_scraped: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
