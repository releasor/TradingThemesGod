"""催化雷达 API。"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_optional_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.catalyst import (
    CatalystEnsureResponse,
    CatalystFeedResponse,
    CatalystThemeSummaryResponse,
)
from app.services.catalyst import CatalystService

router = APIRouter(prefix="/catalysts", tags=["catalysts"])


@router.get("/feed", response_model=CatalystFeedResponse)
async def get_catalyst_feed(
    freshness: str | None = Query(None, description="新鲜度筛选"),
    actor_type: str | None = Query(None, description="主体类型筛选"),
    theme_id: int | None = Query(None, description="题材 ID"),
    q: str | None = Query(None, description="标题/摘要关键词"),
    start: datetime | None = Query(None, alias="from", description="起始时间"),
    end: datetime | None = Query(None, alias="to", description="结束时间"),
    limit: int = Query(default=30, ge=1, le=100, description="分页大小"),
    offset: int = Query(default=0, ge=0, description="分页偏移"),
    db: AsyncSession = Depends(get_db),
):
    """左栏催化事件时间流。"""
    return await CatalystService(db).get_feed(
        freshness=freshness,
        actor_type=actor_type,
        theme_id=theme_id,
        q=q,
        start=start,
        end=end,
        limit=limit,
        offset=offset,
    )


@router.get("/themes/{theme_id}/summary", response_model=CatalystThemeSummaryResponse)
async def get_catalyst_theme_summary(
    theme_id: int,
    db: AsyncSession = Depends(get_db),
):
    """右栏题材摘要（含分类计数与相关新闻标题）。"""
    return await CatalystService(db).get_theme_summary(theme_id)


@router.post("/classify/ensure", response_model=CatalystEnsureResponse)
async def ensure_catalyst_classify(
    days: int = Query(default=7, ge=1, le=90, description="回溯天数"),
    use_model: bool = Query(default=False, description="是否入队模型重标（需登录）"),
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    """幂等确保近 N 日事件具备规则分类；模型重标仅登录且显式开启时入队。"""
    effective_use_model = user is not None and use_model
    user_id = user.id if user else None
    return await CatalystService(db).ensure_classify(
        days=days,
        use_model=effective_use_model,
        user_id=user_id,
    )
