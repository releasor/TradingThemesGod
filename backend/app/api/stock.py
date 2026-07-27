"""股票和事件 API 端点

提供股票查询、详情、事件列表与 AI 研判报告接口。
"""

import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.stock import (
    EventListResponse,
    StockDetailResponse,
    StockListResponse,
)
from app.schemas.stock_ai_report import (
    StockAiReportGenerateRequest,
    StockAiReportResponse,
)
from app.services.stock import StockService
from app.services.stock_ai_report import StockAiReportService

STOCK_CODE_PATTERN = re.compile(r"^\d{6}$")

router = APIRouter(tags=["stocks"])


def _require_stock_code(code: str) -> str:
    if not STOCK_CODE_PATTERN.match(code):
        raise HTTPException(status_code=400, detail="股票代码格式错误，应为6位数字")
    return code


@router.get("/stocks", response_model=StockListResponse)
async def list_stocks(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    sort_by: Literal[
        "code", "name", "industry", "market_cap", "current_price", "rise_fall_pct"
    ] = Query(default="code", description="排序字段"),
    order: Literal["asc", "desc"] = Query(default="asc", description="排序方向"),
    industry: str | None = Query(default=None, description="按行业筛选"),
    exchange: Literal["SH", "SZ", "BJ"] | None = Query(
        default=None, description="按交易所筛选(SH/SZ/BJ)"
    ),
    db: AsyncSession = Depends(get_db),
):
    """获取股票列表

    支持分页、排序和筛选。
    """
    service = StockService(db)
    return await service.list_stocks(
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        order=order,
        industry=industry,
        exchange=exchange,
    )


@router.get("/events", response_model=EventListResponse)
async def list_events(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    event_type: str | None = Query(default=None, description="按事件类型筛选"),
    sort_by: Literal["title", "event_type", "published_at"] = Query(
        default="published_at", description="排序字段"
    ),
    order: Literal["asc", "desc"] = Query(default="desc", description="排序方向"),
    db: AsyncSession = Depends(get_db),
):
    """获取事件列表

    支持分页、排序和按事件类型筛选。
    """
    service = StockService(db)
    return await service.list_events(
        page=page,
        page_size=page_size,
        event_type=event_type,
        sort_by=sort_by,
        order=order,
    )


@router.get("/stocks/{code}/ai-report", response_model=StockAiReportResponse)
async def get_stock_ai_report(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """读取当前用户对该股缓存的最近一份 AI 研判报告。"""
    _require_stock_code(code)
    return await StockAiReportService(db, current_user.id).get_cached(code)


@router.post("/stocks/{code}/ai-report", response_model=StockAiReportResponse)
async def generate_stock_ai_report(
    code: str,
    body: StockAiReportGenerateRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """生成或强制刷新个股 AI 买入/持有研判报告。"""
    _require_stock_code(code)
    force = body.force if body else False
    return await StockAiReportService(db, current_user.id).generate(code, force=force)


@router.get("/stocks/{code}", response_model=StockDetailResponse)
async def get_stock_detail(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    """获取股票详情

    返回股票详细信息，包括最近5条事件。
    """
    _require_stock_code(code)
    service = StockService(db)
    return await service.get_stock_detail(code=code)


@router.get("/stocks/{code}/events", response_model=EventListResponse)
async def get_stock_events(
    code: str,
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
):
    """获取股票的事件列表

    返回指定股票的事件，按发布时间降序排列。
    """
    _require_stock_code(code)
    service = StockService(db)
    return await service.get_stock_events(
        code=code,
        page=page,
        page_size=page_size,
    )
