"""实时财经新闻 API。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.news import NewsRepository
from app.schemas.news import NewsListResponse, NewsRefreshRequest, NewsRefreshResponse
from app.services.news import NewsService

router = APIRouter(prefix="/news", tags=["news"])


@router.get("", response_model=NewsListResponse)
async def list_news(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    source: str | None = Query(default=None, max_length=50),
    sources: str | None = Query(default=None, max_length=1000),
    category: str | None = Query(default=None, max_length=30),
    db: AsyncSession = Depends(get_db),
):
    repository = NewsRepository(db)
    selected_sources = {item for item in (sources or "").split(",") if item} or None
    items, total = await repository.list_latest(
        limit, source, category, sources=selected_sources, offset=offset
    )
    return NewsListResponse(items=items, total=total)


@router.get("/sources", response_model=list[str])
async def list_news_sources(db: AsyncSession = Depends(get_db)):
    return NewsService(NewsRepository(db)).available_source_names


@router.post("/refresh", response_model=NewsRefreshResponse)
async def refresh_news(
    request: NewsRefreshRequest | None = None, db: AsyncSession = Depends(get_db)
):
    try:
        source_names = (
            set(request.sources)
            if request is not None and request.sources is not None
            else None
        )
        return await NewsService(NewsRepository(db)).refresh(source_names)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
