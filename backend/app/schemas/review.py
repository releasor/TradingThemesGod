"""复盘台 API 模型。"""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class ReviewRunBrief(BaseModel):
    """复盘 run 摘要。"""

    id: int
    trade_date: date
    run_type: str
    status: str
    source_status: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime | None = None
    finished_at: datetime | None = None


class ReviewCandidateItem(BaseModel):
    """复盘候选投影。"""

    stock_id: int
    stock_code: str | None = None
    stock_name: str | None = None
    theme_id: int | None = None
    theme_name: str | None = None
    strategy: str = ""
    score: int = 0
    rank: int = 0
    decision: str = ""


class ReviewStageTransition(BaseModel):
    """题材阶段迁移。"""

    theme_id: int
    theme_name: str | None = None
    from_stage: str | None = None
    to_stage: str
    strength_score: int | float | None = None


class ReviewCandidatePerformance(BaseModel):
    """单只候选涨跌验证。"""

    stock_id: int
    stock_code: str | None = None
    stock_name: str | None = None
    same_day_pct: float | None = None
    next_day_pct: float | None = None
    reason: str | None = None


class ReviewPerformance(BaseModel):
    """当日涨跌验证聚合。"""

    candidates: list[ReviewCandidatePerformance] = Field(default_factory=list)


class ReviewThemeDayPoint(BaseModel):
    """题材轴单日轨迹点。"""

    trade_date: date
    stage: str
    strength_score: int | float = 0
    rise_fall_pct: float | None = None


class ReviewDayResponse(BaseModel):
    """交易日轴复盘聚合。"""

    trade_date: date
    degraded: bool = False
    missing_sources: list[str] = Field(default_factory=list)
    runs: list[ReviewRunBrief] = Field(default_factory=list)
    strategy_card: dict[str, Any] | None = None
    candidates: list[ReviewCandidateItem] = Field(default_factory=list)
    stage_transitions: list[ReviewStageTransition] = Field(default_factory=list)
    performance: ReviewPerformance | None = None
    report_summary: str | None = None


class ReviewThemeResponse(BaseModel):
    """题材轴复盘聚合。"""

    theme_id: int
    theme_name: str
    days: int
    trajectory: list[ReviewThemeDayPoint] = Field(default_factory=list)
    related_candidates: list[ReviewCandidateItem] = Field(default_factory=list)
    run_refs: list[ReviewRunBrief] = Field(default_factory=list)


class ReviewDayListResponse(BaseModel):
    """有复盘数据的交易日列表。"""

    items: list[date] = Field(default_factory=list)


class ReviewAiReportResponse(BaseModel):
    """复盘 AI/规则日报。"""

    trade_date: date
    user_id: int | None = None
    status: str
    content_md: str = ""
    content_json: dict[str, Any] = Field(default_factory=dict)
    model_name: str | None = None
    error: str | None = None
    source_run_ids: list[Any] = Field(default_factory=list)
