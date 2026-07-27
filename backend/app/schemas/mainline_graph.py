"""主线图谱 API 模型。"""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.concept_graph import ConceptGraphResponse


class MainlineGraphVersionMeta(BaseModel):
    id: int
    trade_date: date
    kind: str
    title: str | None = None
    status: str
    parent_version_id: int | None = None
    created_by: int | None = None
    published_at: datetime | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class MainlineGraphNodeItem(BaseModel):
    id: int
    theme_id: int
    theme_name: str = ""
    mainline_score: int = 0
    strength_score: int = 0
    lifecycle_stage: str
    role: str
    payload: dict[str, Any] | None = None


class MainlineGraphEdgeItem(BaseModel):
    id: int
    from_theme_id: int
    to_theme_id: int
    weight: float
    method: str
    status: str
    rationale: str = ""
    created_by: int | None = None


class MainlineGraphViewResponse(BaseModel):
    trade_date: date
    version: MainlineGraphVersionMeta | None = None
    nodes: list[MainlineGraphNodeItem] = Field(default_factory=list)
    edges: list[MainlineGraphEdgeItem] = Field(default_factory=list)
    empty: bool = False


class MainlineGraphVersionListResponse(BaseModel):
    trade_date: date
    items: list[MainlineGraphVersionMeta] = Field(default_factory=list)


class MainlineGraphEnsureRequest(BaseModel):
    trade_date: date | None = None
    use_model: bool = False


class MainlineGraphEnsureResponse(BaseModel):
    trade_date: date
    version_id: int
    node_count: int = 0
    edge_count: int = 0
    model_queued: bool = False
    generated_at: datetime | None = None
    elapsed_ms: int = 0


class MainlineGraphCreateDraftRequest(BaseModel):
    trade_date: date | None = None
    source_version_id: int | None = None
    title: str | None = None


class MainlineGraphEdgePatch(BaseModel):
    op: Literal["upsert", "delete"]
    edge_id: int | None = None
    from_theme_id: int | None = None
    to_theme_id: int | None = None
    weight: float | None = None
    method: str = "manual"
    status: str = "active"
    rationale: str = ""


class MainlineGraphPatchEdgesRequest(BaseModel):
    edges: list[MainlineGraphEdgePatch] = Field(default_factory=list)


class MainlineGraphAcceptEdgeRequest(BaseModel):
    draft_version_id: int


class MainlineGraphThemeConceptResponse(BaseModel):
    theme_id: int
    theme_name: str = ""
    trade_date: date | None = None
    lifecycle_stage: str | None = None
    strength_score: int | None = None
    mainline_score: int | None = None
    concept_graph: ConceptGraphResponse = Field(default_factory=ConceptGraphResponse)
