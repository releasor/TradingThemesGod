"""题材档案、驱动事件与市场快照的数据契约。"""

from datetime import date, datetime

from pydantic import BaseModel, Field, computed_field


class ThemeSourceReference(BaseModel):
    title: str
    url: str
    publisher: str | None = None
    published_at: datetime | None = None


class ThemeProfileResponse(BaseModel):
    definition: str
    core_logic: str
    applications: list[str]
    catalysts: list[str]
    risks: list[str]
    sources: list[ThemeSourceReference]
    generated_at: datetime

    model_config = {"from_attributes": True}


class ThemeDriverEventResponse(BaseModel):
    id: int
    title: str
    summary: str
    source: str
    url: str
    published_at: datetime
    relevance_score: int = Field(ge=0, le=100)
    crawled_at: datetime

    model_config = {"from_attributes": True}


class ThemeMarketSnapshotResponse(BaseModel):
    trade_date: date
    up_count: int = Field(ge=0)
    down_count: int = Field(ge=0)
    flat_count: int = Field(ge=0)
    suspended_count: int = Field(ge=0)
    limit_up_count: int | None = Field(default=None, ge=0)
    limit_down_count: int | None = Field(default=None, ge=0)
    calculated_at: datetime

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def up_down_ratio(self) -> float | None:
        return round(self.up_count / self.down_count, 2) if self.down_count else None

    @computed_field
    @property
    def up_down_display(self) -> str:
        return f"{self.up_count}:{self.down_count}"


class ExtractedThemeProfile(BaseModel):
    definition: str = Field(min_length=1, max_length=4000)
    core_logic: str = Field(min_length=1, max_length=4000)
    applications: list[str] = Field(default_factory=list)
    catalysts: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)


class ExtractedDriverEvent(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    summary: str = Field(min_length=1, max_length=2000)
    source_url: str
    published_at: datetime
    relevance_score: int = Field(ge=0, le=100)


class ExtractedThemeInsights(BaseModel):
    profile: ExtractedThemeProfile | None = None
    events: list[ExtractedDriverEvent] = Field(default_factory=list)


class ThemeInsightRefreshResponse(BaseModel):
    theme_id: int
    theme_name: str
    profile_updated: bool
    candidate_events: int = 0
    inserted_events: int = 0
    updated_events: int = 0
    ignored_events: int = 0
    successful_sources: list[str] = Field(default_factory=list)
    failed_sources: list[str] = Field(default_factory=list)
    degraded: bool = False
    elapsed_ms: int = Field(default=0, description="刷新耗时（毫秒）")
    refreshed_at: datetime
    message: str
    model_name: str | None = Field(default=None, description="实际调用的模型名")
    model_error: str | None = Field(default=None, description="模型调用/解析失败原因")
    model_reasoning: str | None = Field(
        default=None, description="模型思考/推理过程（若厂商返回）"
    )
    model_raw_response: str | None = Field(
        default=None, description="模型原始返回预览（截断）"
    )
    source_count: int = Field(default=0, description="成功抓取的来源条数")
