"""短线机会雷达 API。"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.short_term import (
    FirstToSecondCandidateResponse,
    SectorRotationResponse,
    ShortTermOverviewResponse,
    ShortTermPeriod,
    ShortTermSignalRefreshResponse,
    ThemeLifecycleResponse,
)
from app.services.first_to_second import FirstToSecondService
from app.services.model_provider import ModelProviderService
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


def _overview_query_params(
    trade_date: date | None,
    period: ShortTermPeriod,
    start_date: date | None,
    end_date: date | None,
) -> tuple[date | None, ShortTermPeriod, date | None, date | None]:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=422, detail="自定义开始日期不能晚于结束日期")
    return trade_date, period, start_date, end_date


@router.post("/signals/refresh", response_model=ShortTermSignalRefreshResponse)
async def refresh_short_term_signals(
    trade_date: date | None = Query(default=None, description="交易日"),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """全量采集短线信号并重建轮动/生命周期快照（需登录）。"""
    return await ShortTermService(db).refresh_signals(trade_date)


@router.get("/sectors", response_model=SectorRotationResponse)
async def list_short_term_sectors(
    trade_date: date | None = Query(default=None, description="交易日"),
    source: str | None = Query(
        default=None, description="题材数据源过滤；缺省为默认看板源 eastmoney"
    ),
    db: AsyncSession = Depends(get_db),
):
    """主线/轮动题材列表（含生命周期与强度）。"""
    return await ShortTermService(db).get_sectors(trade_date, source=source)


@router.get("/themes/{theme_id}/lifecycle", response_model=ThemeLifecycleResponse)
async def get_theme_lifecycle(
    theme_id: int,
    days: int = Query(default=10, ge=1, le=60, description="回溯交易日数"),
    db: AsyncSession = Depends(get_db),
):
    """题材近 N 日生命周期与强度轨迹。"""
    return await ShortTermService(db).get_theme_lifecycle(theme_id, days=days)


@router.post("/overview/refresh-data", response_model=ShortTermOverviewResponse)
async def refresh_short_term_data(
    trade_date: date | None = Query(default=None, description="交易日"),
    period: ShortTermPeriod = Query(default="today", description="统计周期"),
    start_date: date | None = Query(default=None, description="自定义开始日期"),
    end_date: date | None = Query(default=None, description="自定义结束日期"),
    db: AsyncSession = Depends(get_db),
):
    """拉取最新行情并刷新指数情绪策略卡。"""
    trade_date, period, start_date, end_date = _overview_query_params(
        trade_date, period, start_date, end_date
    )
    try:
        return await ShortTermService(db).refresh_data_and_get_overview(
            trade_date, period, start_date=start_date, end_date=end_date
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/overview/analyze", response_model=ShortTermOverviewResponse)
async def analyze_short_term_from_database(
    trade_date: date | None = Query(default=None, description="交易日"),
    period: ShortTermPeriod = Query(default="today", description="统计周期"),
    start_date: date | None = Query(default=None, description="自定义开始日期"),
    end_date: date | None = Query(default=None, description="自定义结束日期"),
    db: AsyncSession = Depends(get_db),
):
    """仅依据数据库已有数据重新分析指数情绪策略卡。"""
    trade_date, period, start_date, end_date = _overview_query_params(
        trade_date, period, start_date, end_date
    )
    try:
        return await ShortTermService(db).analyze_from_database(
            trade_date, period, start_date=start_date, end_date=end_date
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/first-to-second", response_model=FirstToSecondCandidateResponse)
async def get_first_to_second_candidates(
    trade_date: date | None = Query(default=None, description="交易日"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取一进二打板候选。"""
    return await FirstToSecondService(
        db, model_service=ModelProviderService(db, current_user.id)
    ).get_candidates(trade_date, force_refresh=False)


@router.post(
    "/first-to-second/refresh", response_model=FirstToSecondCandidateResponse
)
async def refresh_first_to_second_candidates(
    trade_date: date | None = Query(default=None, description="交易日"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """实时刷新一进二打板候选。"""
    return await FirstToSecondService(
        db, model_service=ModelProviderService(db, current_user.id)
    ).get_candidates(trade_date, force_refresh=True)
