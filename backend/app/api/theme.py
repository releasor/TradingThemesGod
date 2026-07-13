"""题材 API 端点

提供题材查询、搜索、排名和分类接口。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.theme import ThemeService
from app.schemas.theme import (
    ThemeCategoriesResponse,
    ThemeDetailResponse,
    ThemeListResponse,
    ThemeRankingResponse,
)

router = APIRouter(prefix="/themes", tags=["themes"])


@router.get("", response_model=ThemeListResponse)
async def list_themes(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    sort_by: str = Query(default="heat_index", description="排序字段: heat_index/rise_fall_pct"),
    sort_order: str = Query(default="desc", description="排序方向: asc/desc"),
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
    q: str = Query(description="搜索关键词"),
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
