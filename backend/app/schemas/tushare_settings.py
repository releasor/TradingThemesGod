"""Tushare 数据源配置 schemas。"""

from datetime import datetime

from pydantic import BaseModel, Field


class TushareSettingsResponse(BaseModel):
    enabled: bool
    has_token: bool
    updated_at: datetime | None = None


class TushareSettingsUpdate(BaseModel):
    enabled: bool
    token: str | None = Field(
        default=None,
        description="新 Token；省略或空字符串表示保留已有密文",
    )


class TushareTestRequest(BaseModel):
    token: str | None = Field(
        default=None,
        description="可选临时 Token；省略则用当前生效凭据",
    )


class TushareTestResponse(BaseModel):
    success: bool
    message: str
