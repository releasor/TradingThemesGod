"""题材挖掘 API 模型。"""

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class MiningMemberItem(BaseModel):
    """挖掘卡成份股。"""

    stock_id: int
    stock_code: str | None = None
    stock_name: str | None = None
    concept_node_id: int | None = None
    concept_node_name: str | None = None
    score: int = 0
    rank: int = 0
    role_tag: str = ""
    metrics: dict[str, Any] = Field(default_factory=dict)
    rise_fall_pct: float | None = None


class MiningNoteResponse(BaseModel):
    """用户模型点评。"""

    id: int
    card_id: int
    user_id: int
    status: str
    content_md: str = ""
    model_name: str | None = None
    error: str | None = None


class MiningCardItem(BaseModel):
    """题材挖掘卡（board 预览或详情）。"""

    id: int
    trade_date: date
    theme_id: int
    theme_name: str = ""
    mining_type: str
    score: int = 0
    rank: int = 0
    lifecycle_stage: str
    strength_score: int = 0
    rationale: str = ""
    score_breakdown: dict[str, Any] = Field(default_factory=dict)
    degraded: bool = False
    missing_metrics: list[Any] = Field(default_factory=list)
    member_count: int = 0
    members: list[MiningMemberItem] = Field(default_factory=list)
    note: MiningNoteResponse | None = None


class MiningBoardResponse(BaseModel):
    """三列题材挖掘看板。"""

    trade_date: date
    low_branch: list[MiningCardItem] = Field(default_factory=list)
    catch_up: list[MiningCardItem] = Field(default_factory=list)
    hidden_leader: list[MiningCardItem] = Field(default_factory=list)


class MiningEnsureResponse(BaseModel):
    """ensure 重算结果。"""

    trade_date: date
    theme_count: int = 0
    card_count: int = 0
    counts: dict[str, int] = Field(default_factory=dict)
