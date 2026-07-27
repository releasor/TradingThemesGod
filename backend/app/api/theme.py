"""题材 API 端点

提供题材查询、搜索、排名和分类接口。
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.theme import Theme
from app.schemas.concept_refresh import (
    ConceptGraphBatchItem,
    ConceptGraphBatchRequest,
    ConceptGraphBatchResponse,
    ConceptGraphRefreshResponse,
)
from app.schemas.stock import StockListResponse
from app.schemas.theme import (
    ThemeCategoriesResponse,
    ThemeDetailResponse,
    ThemeListResponse,
    ThemeRankingResponse,
)
from app.schemas.theme_insight import ThemeInsightRefreshResponse
from app.services.concept_graph_refresh import ConceptGraphRefreshService
from app.services.model_provider import ModelProviderService
from app.services.theme import ThemeService
from app.services.theme_insight import ThemeInsightRefreshService

router = APIRouter(prefix="/themes", tags=["themes"])


def _concept_service(
    db: AsyncSession, current_user: User
) -> ConceptGraphRefreshService:
    return ConceptGraphRefreshService(
        db, providers=ModelProviderService(db, current_user.id)
    )


def _insight_service(db: AsyncSession, current_user: User) -> ThemeInsightRefreshService:
    return ThemeInsightRefreshService(
        db, providers=ModelProviderService(db, current_user.id)
    )


@router.post("/concept-graphs/refresh", response_model=ConceptGraphBatchResponse)
async def refresh_concept_graphs(
    payload: ConceptGraphBatchRequest,
    current_user: User = Depends(get_current_user),
):
    """有限批量更新题材图谱，逐个处理并返回每项结果。"""
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        query = select(Theme.id).where(Theme.deleted_at.is_(None)).order_by(Theme.id)
        if payload.theme_ids:
            query = query.where(Theme.id.in_(payload.theme_ids))
        theme_ids = list((await db.execute(query.limit(payload.limit))).scalars())

    service = ConceptGraphRefreshService(user_id=current_user.id)
    items: list[ConceptGraphBatchItem] = []
    try:
        for theme_id in theme_ids:
            try:
                result = await service.refresh(theme_id)
                items.append(
                    ConceptGraphBatchItem(theme_id=theme_id, success=True, result=result)
                )
            except HTTPException as exc:
                items.append(
                    ConceptGraphBatchItem(
                        theme_id=theme_id, success=False, error=str(exc.detail)
                    )
                )
    finally:
        await service.research.middleware.close()
    return ConceptGraphBatchResponse(items=items)


@router.get("", response_model=ThemeListResponse)
async def list_themes(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    sort_by: Literal["heat_index", "rise_fall_pct", "stock_count", "name"] = Query(
        default="heat_index", description="排序字段"
    ),
    sort_order: Literal["asc", "desc"] = Query(default="desc", description="排序方向"),
    category: str | None = Query(default=None, description="按分类筛选"),
    tags: str | None = Query(default=None, description="按标签筛选（逗号分隔）"),
    db: AsyncSession = Depends(get_db),
):
    """获取题材列表

    支持分页、排序和筛选。
    """
    service = ThemeService(db)
    return await service.list_themes(
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        category=category,
        tags=tags,
    )


@router.get("/ranking", response_model=ThemeRankingResponse)
async def get_theme_ranking(
    limit: int = Query(default=20, ge=1, le=100, description="返回数量"),
    db: AsyncSession = Depends(get_db),
):
    """获取题材排名

    按热度指数降序返回前 N 个题材。
    """
    service = ThemeService(db)
    return await service.get_ranking(limit=limit)


@router.get("/categories", response_model=ThemeCategoriesResponse)
async def get_theme_categories(
    db: AsyncSession = Depends(get_db),
):
    """获取所有题材分类

    返回所有唯一的分类值。
    """
    service = ThemeService(db)
    return await service.get_categories()


@router.get("/search", response_model=ThemeListResponse)
async def search_themes(
    q: str = Query(description="搜索关键词", min_length=1, max_length=100),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
):
    """搜索题材

    在题材名称和描述中搜索关键词。
    """
    service = ThemeService(db)
    return await service.search_themes(
        query=q,
        page=page,
        page_size=page_size,
    )


@router.get("/market-signals", response_model=ThemeRankingResponse)
async def get_market_signals(
    db: AsyncSession = Depends(get_db),
):
    """获取独立于实际题材的市场表现板块。"""
    service = ThemeService(db)
    return await service.get_market_signals()


@router.get("/indicator-signals", response_model=ThemeRankingResponse)
async def get_indicator_signals(
    db: AsyncSession = Depends(get_db),
):
    """获取独立于实际题材的行情指标板块（新高、财报预告、破增发等）。"""
    service = ThemeService(db)
    return await service.get_indicator_signals()


@router.post(
    "/{theme_id}/concept-graph/refresh",
    response_model=ConceptGraphRefreshResponse,
)
async def refresh_concept_graph(
    theme_id: int,
    current_user: User = Depends(get_current_user),
):
    """抓取公开资料并使用默认模型增量刷新单个题材图谱。"""
    service = ConceptGraphRefreshService(user_id=current_user.id)
    try:
        return await service.refresh(theme_id)
    finally:
        await service.research.middleware.close()


@router.post(
    "/{theme_id}/insights/refresh",
    response_model=ThemeInsightRefreshResponse,
)
async def refresh_theme_insights(
    theme_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """抓取公开资料并增量刷新单个题材的介绍和驱动事件。"""
    service = _insight_service(db, current_user)
    try:
        return await service.refresh(theme_id)
    finally:
        await service.research.middleware.close()


@router.get("/{theme_id}/stocks", response_model=StockListResponse)
async def get_theme_stocks(
    theme_id: int,
    chain_level: Literal["upstream", "midstream", "downstream"] | None = Query(
        default=None, description="产业链层级"
    ),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
):
    """获取题材关联的股票列表

    返回指定题材下的股票，支持按产业链层级筛选。
    """
    service = ThemeService(db)
    return await service.get_theme_stocks(
        theme_id=theme_id,
        chain_level=chain_level,
        page=page,
        page_size=page_size,
    )


@router.get("/{theme_id}", response_model=ThemeDetailResponse)
async def get_theme_detail(
    theme_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取题材详情

    返回题材详细信息，包括产业链数据（按层级分组）。
    """
    service = ThemeService(db)
    return await service.get_theme_detail(theme_id=theme_id)


@router.get("/export/csv")
async def export_themes_csv(
    category: str | None = Query(default=None, description="按分类筛选"),
    db: AsyncSession = Depends(get_db),
):
    """导出题材数据为 CSV 格式

    使用服务端游标流式读取，内存占用 O(1)。
    """
    service = ThemeService(db)

    return StreamingResponse(
        service.stream_export_csv(category=category),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=themes_export.csv"},
    )
