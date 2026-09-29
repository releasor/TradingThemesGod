"""Prompt 工作台 Pydantic schemas。"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PromptItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1)
    category: str | None = Field(default=None, max_length=100)
    tags: list[str] = Field(default_factory=list)
    enabled: bool = True
    pinned: bool = False
    sort_order: int = 0


class PromptItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = Field(default=None, min_length=1)
    category: str | None = None
    tags: list[str] | None = None
    enabled: bool | None = None
    pinned: bool | None = None
    sort_order: int | None = None


class PromptItemResponse(BaseModel):
    id: int
    user_id: int
    title: str
    body: str
    category: str | None
    tags: list[str]
    enabled: bool
    pinned: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DesignRequest(BaseModel):
    goal: str = Field(min_length=1)
    notes: str | None = None
    provider_id: int | None = None


class OptimizeRequest(BaseModel):
    source: str = Field(min_length=1)
    mode: Literal["smart", "framework"] = "smart"
    framework: str | None = None
    extra_goal: str | None = None
    provider_id: int | None = None
    persist: bool = True


class IterateRequest(BaseModel):
    run_id: int | None = None
    current: str = Field(min_length=1)
    instruction: str = Field(min_length=1)
    provider_id: int | None = None


class DualTestRequest(BaseModel):
    prompt_a: str = Field(min_length=1)
    prompt_b: str = Field(min_length=1)
    user_message: str = Field(min_length=1)
    provider_id: int | None = None


class TextResult(BaseModel):
    result: str
    run_id: int | None = None


class DualTestResult(BaseModel):
    output_a: str
    output_b: str


class OptimizeRunResponse(BaseModel):
    id: int
    source: str
    result: str
    mode: str
    framework: str | None
    extra_goal: str | None
    versions: list
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OptimizeRunSummary(BaseModel):
    id: int
    source: str
    result: str
    mode: str
    framework: str | None
    extra_goal: str | None
    version_count: int
    created_at: datetime
    updated_at: datetime


class ChatSessionCreate(BaseModel):
    title: str = Field(default="新对话", max_length=200)
    provider_id: int | None = None


class ChatSessionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    provider_id: int | None = None


class ChatSessionResponse(BaseModel):
    id: int
    user_id: int
    title: str
    provider_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatMessageCreate(BaseModel):
    content: str = Field(min_length=1)
    provider_id: int | None = None


class ChatMessageResponse(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}
