"""个人 AI OS Pydantic schemas。"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class MemoryPolicy(BaseModel):
    inject_profile: bool = True
    note_top_k: int = Field(default=5, ge=0, le=50)
    recent_turns: int = Field(default=20, ge=1, le=100)


class ModuleFlags(BaseModel):
    chat: bool = True
    memory: bool = True
    journal: bool = True
    reports: bool = True
    decisions: bool = True


class ModelPrefs(BaseModel):
    default_provider_id: int | None = None
    compare_provider_ids: list[int] = Field(default_factory=list)


class OsProfileResponse(BaseModel):
    id: int
    user_id: int
    display_name: str | None
    goals: str | None
    health_baseline: dict[str, Any]
    system_prompt: str
    memory_policy: dict[str, Any]
    module_flags: dict[str, Any]
    model_prefs: dict[str, Any]
    report_prompt_appendix: str | None
    decision_prompt_appendix: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OsProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    goals: str | None = None
    health_baseline: dict[str, Any] | None = None
    system_prompt: str | None = Field(default=None, min_length=1)
    memory_policy: MemoryPolicy | None = None
    module_flags: ModuleFlags | None = None
    model_prefs: ModelPrefs | None = None
    report_prompt_appendix: str | None = None
    decision_prompt_appendix: str | None = None


class OsNoteCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)


class OsNoteUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = Field(default=None, min_length=1)
    tags: list[str] | None = None


class OsNoteResponse(BaseModel):
    id: int
    user_id: int
    title: str
    body: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OsChatSessionCreate(BaseModel):
    title: str = Field(default="新对话", max_length=200)
    provider_id: int | None = None


class OsChatSessionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    provider_id: int | None = None


class OsChatSessionResponse(BaseModel):
    id: int
    user_id: int
    title: str
    provider_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OsChatMessageCreate(BaseModel):
    content: str = Field(min_length=1)
    provider_id: int | None = None


class OsChatMessageResponse(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    provider_id: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


JournalKind = Literal["diet", "training", "sleep", "schedule"]


class OsJournalCreate(BaseModel):
    kind: JournalKind
    occurred_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)
    note: str | None = None
    media_refs: list[str] = Field(default_factory=list)


class OsJournalUpdate(BaseModel):
    kind: JournalKind | None = None
    occurred_at: datetime | None = None
    payload: dict[str, Any] | None = None
    note: str | None = None
    media_refs: list[str] | None = None


class OsJournalResponse(BaseModel):
    id: int
    user_id: int
    kind: str
    occurred_at: datetime
    payload: dict[str, Any]
    note: str | None
    media_refs: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OsReportGenerateRequest(BaseModel):
    report_date: date | None = None
    provider_id: int | None = None


class OsReportFeedbackRequest(BaseModel):
    score: int = Field(ge=1, le=5)
    note: str | None = None
    apply_to_prompt: bool = True


class OsDailyReportResponse(BaseModel):
    id: int
    user_id: int
    report_date: date
    content: str
    provider_id: int | None
    entry_ids: list[int]
    feedback_score: int | None
    feedback_note: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OsDecisionCreate(BaseModel):
    question: str = Field(min_length=1)
    constraints: str | None = None


class OsDecisionRunRequest(BaseModel):
    provider_ids: list[int] | None = None
    summarize_provider_id: int | None = None


class OsDecisionChooseRequest(BaseModel):
    option_id: int
    outcome_note: str | None = None


class OsDecisionOptionFeedback(BaseModel):
    score: float = Field(ge=0, le=10)
    note: str | None = None
    apply_to_prompt: bool = True


class OsScoutTemplate(BaseModel):
    id: str
    title: str
    question: str
    constraints: str
    hint: str


DashboardSourceType = Literal[
    "chat_session", "note", "journal", "report", "decision"
]


class OsDashboardPinCreate(BaseModel):
    source_type: DashboardSourceType
    source_id: int = Field(ge=1)
    title: str | None = Field(default=None, max_length=240)
    snippet: str | None = None


class OsDashboardPinUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=240)
    snippet: str | None = None
    sort_order: int | None = None


class OsDashboardPinResponse(BaseModel):
    id: int
    user_id: int
    source_type: str
    source_id: int
    title: str
    snippet: str | None
    sort_order: int
    href: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OsDashboardCounts(BaseModel):
    chat_sessions: int = 0
    notes: int = 0
    journal: int = 0
    reports: int = 0
    decisions: int = 0
    pins: int = 0


class OsDashboardJournalByKind(BaseModel):
    diet: int = 0
    training: int = 0
    sleep: int = 0
    schedule: int = 0


class OsDashboardRecentItem(BaseModel):
    id: int
    source_type: DashboardSourceType
    title: str
    snippet: str | None = None
    href: str
    at: datetime | None = None
    pinned: bool = False


class OsOptimizeTip(BaseModel):
    id: str
    title: str
    body: str
    priority: Literal["high", "medium", "low"] = "medium"
    action_href: str | None = None
    action_label: str | None = None


class OsDashboardOverview(BaseModel):
    display_name: str | None = None
    goals: str | None = None
    health_baseline: dict[str, Any] = Field(default_factory=dict)
    module_flags: dict[str, Any] = Field(default_factory=dict)
    has_report_tuning: bool = False
    has_decision_tuning: bool = False
    data_readiness: Literal["empty", "warmup", "ready"] = "empty"
    counts: OsDashboardCounts
    journal_by_kind: OsDashboardJournalByKind
    recent: list[OsDashboardRecentItem] = Field(default_factory=list)
    pins: list[OsDashboardPinResponse] = Field(default_factory=list)
    optimize_tips: list[OsOptimizeTip] = Field(default_factory=list)


class OsDecisionOptionResponse(BaseModel):
    id: int
    run_id: int
    tier: str
    title: str
    content: str
    provider_id: int | None
    raw_reply: str | None
    selected: bool
    feedback_score: float | None
    feedback_note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class OsDecisionRunResponse(BaseModel):
    id: int
    thread_id: int
    summary: str | None
    provider_ids: list[int]
    options: list[OsDecisionOptionResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class OsDecisionThreadResponse(BaseModel):
    id: int
    user_id: int
    question: str
    constraints: str | None
    status: str
    chosen_option_id: int | None
    outcome_note: str | None
    created_at: datetime
    updated_at: datetime
    latest_run: OsDecisionRunResponse | None = None

    model_config = {"from_attributes": True}
