"""模型服务配置 API 类型。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

ModelProtocol = Literal["openai_compatible", "anthropic", "gemini", "ollama"]


class ModelProviderUpsert(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    protocol: ModelProtocol
    base_url: HttpUrl
    api_key: str = Field(default="", max_length=4000)
    model: str = Field(min_length=1, max_length=200)
    custom_headers: dict[str, str] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=60, ge=5, le=300)
    temperature: float = Field(default=0.1, ge=0, le=2)
    max_tokens: int = Field(default=8192, ge=256, le=131072)
    enabled: bool = True
    is_default: bool = False


class ModelProviderResponse(BaseModel):
    id: int
    name: str
    protocol: ModelProtocol
    base_url: str
    model: str
    has_api_key: bool
    custom_header_names: list[str]
    timeout_seconds: int
    temperature: float
    max_tokens: int
    enabled: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime


class ModelTestResponse(BaseModel):
    success: bool
    message: str
    latency_ms: int


class ModelListResponse(BaseModel):
    models: list[str]
