"""数据统计 API 端点

提供系统数据统计信息。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from app.core.database import get_db
from app.models.theme import Theme
from app.models.stock import Stock
from app.models.event import Event
from app.models.industry_chain import IndustryChain
from app.models.scraper_run import ScraperRun

router = APIRouter(prefix="/stats", tags=["stats"])


async def _query_theme_count(db: AsyncSession) -> int:
    """查询有效题材数量"""
    return (await db.scalar(
        select(func.count()).select_from(Theme).where(Theme.deleted_at.is_(None))
    )) or 0


async def _query_stock_count(db: AsyncSession) -> int:
    """查询股票数量"""
    return (await db.scalar(
        select(func.count()).select_from(Stock)
    )) or 0


async def _query_event_count(db: AsyncSession) -> int:
    """查询事件数量"""
    return (await db.scalar(
        select(func.count()).select_from(Event)
    )) or 0


async def _query_chain_count(db: AsyncSession) -> int:
    """查询产业链数量"""
    return (await db.scalar(
        select(func.count()).select_from(IndustryChain)
    )) or 0


async def _query_last_scraper(db: AsyncSession) -> dict | None:
    """查询最近一次爬虫运行"""
    last_scraper = await db.scalar(
        select(ScraperRun)
        .order_by(ScraperRun.created_at.desc())
        .limit(1)
    )
    if last_scraper is None:
        return None
    return {
        "id": last_scraper.id,
        "source": last_scraper.source,
        "status": last_scraper.status,
        "created_at": last_scraper.created_at.isoformat(),
    }


async def _query_category_stats(db: AsyncSession) -> list[dict]:
    """查询题材分类统计（Top 10）"""
    category_stats = await db.execute(
        select(
            Theme.category,
            func.count().label('count')
        )
        .where(Theme.deleted_at.is_(None), Theme.category.isnot(None))
        .group_by(Theme.category)
        .order_by(func.count().desc())
        .limit(10)
    )
    return [
        {"category": row[0], "count": row[1]}
        for row in category_stats.all()
    ]


@router.get("")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """获取系统数据统计

    返回题材数量、股票数量、事件数量等统计信息。
    使用 asyncio.gather 并行执行所有统计查询，减少响应延迟。
    """
    # AsyncSession does not support concurrent operations on one connection.
    theme_count = await _query_theme_count(db)
    stock_count = await _query_stock_count(db)
    event_count = await _query_event_count(db)
    chain_count = await _query_chain_count(db)
    last_scraper = await _query_last_scraper(db)
    categories = await _query_category_stats(db)

    return {
        "themes": {
            "total": theme_count,
            "categories": categories,
        },
        "stocks": {
            "total": stock_count,
        },
        "events": {
            "total": event_count,
        },
        "chains": {
            "total": chain_count,
        },
        "scraper": {
            "last_run": last_scraper,
        },
    }
