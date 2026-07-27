"""AI 图谱抽取与刷新响应类型。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


def normalize_score(value: object, default: float = 0.5) -> float:
    if isinstance(value, bool) or value is None:
        return default

    labels = {
        "high": 0.9,
        "medium": 0.5,
        "mid": 0.5,
        "moderate": 0.5,
        "low": 0.2,
        "\u9ad8": 0.9,
        "\u4e2d": 0.5,
        "\u4f4e": 0.2,
    }
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in labels:
            return labels[normalized]
        is_percent = normalized.endswith("%")
        if is_percent:
            normalized = normalized[:-1].strip()
        try:
            score = float(normalized)
        except ValueError:
            return default
        if is_percent or score > 1:
            score /= 100
    elif isinstance(value, (int, float)):
        score = float(value)
        if score > 1:
            score /= 100
    else:
        return default

    return min(max(score, 0.0), 1.0)


class ExtractedStockLink(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    relation_type: str = Field(min_length=1, max_length=50)
    rationale: str = Field(min_length=1, max_length=2000)
    relevance_score: float = Field(default=0.5, ge=0, le=1)
    is_core: bool = False
    sources: list[str] = Field(min_length=1, max_length=6)

    @field_validator("relevance_score", mode="before")
    @classmethod
    def normalize_relevance_score(cls, value: object) -> float:
        return normalize_score(value)


class ExtractedConceptNode(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    node_type: str = Field(default="segment", max_length=30)
    description: str | None = Field(default=None, max_length=4000)
    chain_level: Literal["upstream", "midstream", "downstream"] | None = None
    market_logic: str | None = Field(default=None, max_length=4000)
    catalysts: list[str] = Field(default_factory=list, max_length=10)
    risks: list[str] = Field(default_factory=list, max_length=10)
    confidence: float = Field(default=0.5, ge=0, le=1)
    sources: list[str] = Field(min_length=1, max_length=6)
    stocks: list[ExtractedStockLink] = Field(default_factory=list, max_length=100)
    children: list["ExtractedConceptNode"] = Field(default_factory=list, max_length=50)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, value: object) -> float:
        return normalize_score(value)

    @field_validator("catalysts", "risks", mode="before")
    @classmethod
    def normalize_text_items(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        return [normalized] if normalized else []


class ExtractedConceptGraph(BaseModel):
    nodes: list[ExtractedConceptNode] = Field(max_length=50)


class ConceptGraphRefreshResponse(BaseModel):
    theme_id: int
    theme_name: str
    source_count: int
    added_nodes: int
    updated_nodes: int
    stock_links: int
    elapsed_ms: int = Field(default=0, description="刷新耗时（毫秒）")
    refreshed_at: datetime
    message: str


class ConceptGraphBatchRequest(BaseModel):
    theme_ids: list[int] | None = Field(default=None, max_length=20)
    limit: int = Field(default=5, ge=1, le=20)


class ConceptGraphBatchItem(BaseModel):
    theme_id: int
    success: bool
    result: ConceptGraphRefreshResponse | None = None
    error: str | None = None


class ConceptGraphBatchResponse(BaseModel):
    items: list[ConceptGraphBatchItem]
