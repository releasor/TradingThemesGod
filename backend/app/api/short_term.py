"""短线机会雷达 API。"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.short_term import (
    FirstToSecondCandidateResponse,
    ShortTermOverviewResponse,
    ShortTermPeriod,
)
from app.services.first_to_second import FirstToSecondService
from app.services.short_term import ShortTermService

router = APIRouter(prefix="/short-term", tags=["short-term"])


@router.get("/overview", response_model=ShortTermOverviewResponse)
async def get_short_term_overview(
    trade_date: date | None = Query(default=None, description="交易日"),
    period: ShortTermPeriod = Query(default="today", description="统计周期"),
    start_date: date | None = Query(default=None, description="自定义开始日期"),
    end_date: date | None = Query(default=None, description="自定义结束日期"),
    db: AsyncSession = Depends(get_db),
):
    """获取短线雷达概览。"""
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=422, detail="自定义开始日期不能晚于结束日期")
    return await ShortTermService(db).get_overview(
        trade_date, period, start_date=start_date, end_date=end_date
    )


@router.get("/first-to-second", response_model=FirstToSecondCandidateResponse)
async def get_first_to_second_candidates(
    trade_date: date | None = Query(default=None, description="交易日"),
    db: AsyncSession = Depends(get_db),
):
    """获取一进二打板候选。"""
    return await FirstToSecondService(db).get_candidates(
        trade_date, force_refresh=False
    )


@router.post(
    "/first-to-second/refresh", response_model=FirstToSecondCandidateResponse
)
async def refresh_first_to_second_candidates(
    trade_date: date | None = Query(default=None, description="交易日"),
    db: AsyncSession = Depends(get_db),
):
    """实时刷新一进二打板候选。"""
    return await FirstToSecondService(db).get_candidates(
        trade_date, force_refresh=True
    )
