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


@router.get("")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """获取系统数据统计

    返回题材数量、股票数量、事件数量等统计信息。
    """
    # 并行查询各表数量
    theme_count = await db.scalar(
        select(func.count()).select_from(Theme).where(Theme.deleted_at.is_(None))
    )
    stock_count = await db.scalar(
        select(func.count()).select_from(Stock)
    )
    event_count = await db.scalar(
        select(func.count()).select_from(Event)
    )
    chain_count = await db.scalar(
        select(func.count()).select_from(IndustryChain)
    )

    # 获取最近一次爬虫运行
    last_scraper = await db.scalar(
        select(ScraperRun)
        .order_by(ScraperRun.created_at.desc())
        .limit(1)
    )

    # 获取分类统计
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
    categories = [
        {"category": row[0], "count": row[1]}
        for row in category_stats.all()
    ]

    return {
        "themes": {
            "total": theme_count or 0,
            "categories": categories,
        },
        "stocks": {
            "total": stock_count or 0,
        },
        "events": {
            "total": event_count or 0,
        },
        "chains": {
            "total": chain_count or 0,
        },
        "scraper": {
            "last_run": {
                "id": last_scraper.id if last_scraper else None,
                "source": last_scraper.source if last_scraper else None,
                "status": last_scraper.status if last_scraper else None,
                "created_at": last_scraper.created_at.isoformat() if last_scraper else None,
            } if last_scraper else None,
        },
    }
