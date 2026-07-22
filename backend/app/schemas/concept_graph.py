"""概念知识图谱响应模型。"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class SourceReference(BaseModel):
    title: str
    url: str
    publisher: str | None = None
    published_at: str | None = None


class ConceptStockLink(BaseModel):
    code: str
    name: str
    relation_type: str
    rationale: str
    relevance_score: Decimal
    is_core: bool
    sources: list[SourceReference] = Field(default_factory=list)


class ConceptNodeResponse(BaseModel):
    id: int
    name: str
    node_type: str
    description: str | None = None
    chain_level: str | None = None
    market_logic: str | None = None
    catalysts: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    sources: list[SourceReference] = Field(default_factory=list)
    confidence: Decimal
    depth: int
    stocks: list[ConceptStockLink] = Field(default_factory=list)
    children: list["ConceptNodeResponse"] = Field(default_factory=list)


class ConceptGraphResponse(BaseModel):
    roots: list[ConceptNodeResponse] = Field(default_factory=list)
    node_count: int = 0
    stock_count: int = 0
    max_depth: int = 0
    updated_at: datetime | None = None
