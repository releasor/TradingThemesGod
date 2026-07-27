"""催化雷达 API 模型。"""

from datetime import datetime

from pydantic import BaseModel, Field


class CatalystFeedItem(BaseModel):
    """催化 feed 单条。"""

    event_id: int
    theme_id: int
    theme_name: str
    title: str
    summary: str
    source: str
    url: str
    published_at: datetime
    relevance_score: int
    freshness: str
    actor_type: str
    classified_by: str | None = None


class CatalystFeedResponse(BaseModel):
    """催化 feed 列表。"""

    items: list[CatalystFeedItem] = Field(default_factory=list)
    total: int | None = None


class NewsHeadlineItem(BaseModel):
    """题材相关新闻标题（关键词匹配）。"""

    title: str
    url: str
    published_at: datetime
    match_note: str = "关键词匹配"


class CatalystThemeSummaryResponse(BaseModel):
    """右栏题材摘要。"""

    theme_id: int
    theme_name: str
    lifecycle_stage: str | None = None
    strength_score: int | None = None
    counts: dict[str, int] = Field(default_factory=dict)
    recent_events: list[CatalystFeedItem] = Field(default_factory=list)
    news_headlines: list[NewsHeadlineItem] = Field(default_factory=list)


class CatalystEnsureResponse(BaseModel):
    """ensure 分类结果。"""

    classified_rules: int
    model_queued: bool
