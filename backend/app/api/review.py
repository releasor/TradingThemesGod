"""复盘台 API。"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_optional_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.review import (
    ReviewAiReportResponse,
    ReviewDayListResponse,
    ReviewDayResponse,
    ReviewThemeResponse,
)
from app.services.review import ReviewService
from app.services.review_report import ReviewReportService
from app.services.short_term import ShortTermService

router = APIRouter(prefix="/review", tags=["review"])

_DEFAULT_LIST_DAYS = 60


def _resolve_list_range(
    from_date: date | None, to_date: date | None
) -> tuple[date, date]:
    end = to_date or ShortTermService.resolve_trade_date(None)
    start = from_date or (end - timedelta(days=_DEFAULT_LIST_DAYS))
    if start > end:
        raise HTTPException(status_code=422, detail="开始日期不能晚于结束日期")
    return start, end


@router.get("/days", response_model=ReviewDayListResponse)
async def list_review_days(
    from_date: date | None = Query(None, alias="from", description="开始日期"),
    to_date: date | None = Query(None, alias="to", description="结束日期"),
    db: AsyncSession = Depends(get_db),
):
    """列出指定区间内有 run 或可降级投影的交易日。"""
    start, end = _resolve_list_range(from_date, to_date)
    items = await ReviewService(db).list_days(start, end)
    return ReviewDayListResponse(items=items)


@router.get("/days/{trade_date}", response_model=ReviewDayResponse)
async def get_review_day(
    trade_date: date,
    db: AsyncSession = Depends(get_db),
):
    """获取指定交易日的复盘聚合。"""
    return await ReviewService(db).get_day(trade_date)


@router.get("/themes/{theme_id}", response_model=ReviewThemeResponse)
async def get_review_theme(
    theme_id: int,
    days: int = Query(default=10, ge=1, le=60, description="回溯交易日数"),
    db: AsyncSession = Depends(get_db),
):
    """获取题材近 N 日复盘轨迹。"""
    return await ReviewService(db).get_theme(theme_id, days=days)


@router.get("/days/{trade_date}/report", response_model=ReviewAiReportResponse | None)
async def get_review_report(
    trade_date: date,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    """获取当前用户日报；无则回落全局规则摘要。

    尚无日报时返回 ``null``（200），由前端 ensure 生成，避免首屏 404 噪音。
    """
    report_service = ReviewReportService(db)
    report: ReviewAiReportResponse | None = None
    if user is not None:
        report = await report_service.get_report(trade_date, user.id)
    if report is None:
        report = await report_service.get_report(trade_date, None)
    return report


@router.post("/days/{trade_date}/report/ensure", response_model=ReviewAiReportResponse)
async def ensure_review_report(
    trade_date: date,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    """幂等确保日报存在：未登录写规则摘要，登录用户可异步生成 AI 日报。"""
    user_id = user.id if user else None
    return await ReviewReportService(db).ensure(trade_date, user_id)
