"""新闻 API 数据结构。"""

from datetime import datetime

from pydantic import BaseModel, Field


class NewsArticleResponse(BaseModel):
    id: int
    source: str
    category: str
    title: str
    summary: str | None
    url: str
    published_at: datetime
    crawled_at: datetime
    heat_score: int = Field(ge=0, le=100)

    model_config = {"from_attributes": True}


class NewsListResponse(BaseModel):
    items: list[NewsArticleResponse]
    total: int


class NewsSourceResult(BaseModel):
    source: str
    success: bool
    fetched_count: int = 0
    error: str | None = None


class NewsRefreshRequest(BaseModel):
    sources: list[str] | None = None


class NewsRefreshResponse(BaseModel):
    success: bool
    fetched_count: int
    inserted_count: int
    refreshed_at: datetime
    sources: list[NewsSourceResult] = Field(default_factory=list)
