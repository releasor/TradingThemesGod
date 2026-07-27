"""爬虫相关 Pydantic 模型

定义 API 请求和响应的数据结构。
"""

from datetime import date, datetime
from typing import Literal
from pydantic import AliasChoices, BaseModel, Field, field_validator


class ScraperRunRequest(BaseModel):
    """爬虫运行请求"""

    params: dict = Field(default_factory=dict, description="爬虫参数")

    @field_validator('params')
    @classmethod
    def validate_params(cls, v: dict) -> dict:
        """验证爬虫参数"""
        if len(v) > 20:
            raise ValueError('参数数量不能超过20个')
        for key, value in v.items():
            if not isinstance(key, str) or len(key) > 50:
                raise ValueError('参数名必须是字符串且长度不超过50')
            if isinstance(value, str) and len(value) > 500:
                raise ValueError(f'参数 {key} 的值长度不能超过500')
        return v


class ScraperRunResponse(BaseModel):
    """爬虫运行响应"""

    run_id: int = Field(
        validation_alias=AliasChoices("run_id", "id"),
        description="运行记录 ID",
    )
    source: str = Field(description="数据源名称")
    status: str = Field(description="运行状态: running/completed/failed")
    started_at: datetime = Field(description="开始时间")
    finished_at: datetime | None = Field(default=None, description="结束时间")
    items_scraped: int = Field(default=0, description="采集条数")
    error_message: str | None = Field(default=None, description="错误信息")

    model_config = {"from_attributes": True}


class ScraperRunListResponse(BaseModel):
    """爬虫运行列表响应"""

    runs: list[ScraperRunResponse] = Field(description="运行记录列表")
    count: int = Field(description="返回记录数")


class ScraperSourceResponse(BaseModel):
    """爬虫数据源说明。"""

    id: str = Field(description="数据源标识")
    label: str = Field(description="展示名称")
    description: str = Field(description="数据源说明")
    dashboard_selectable: bool = Field(description="是否可在看板全量更新中选择")
    is_default: bool = Field(default=False, description="是否为看板默认数据源")


class ScraperSourceListResponse(BaseModel):
    """爬虫数据源列表响应。"""

    sources: list[ScraperSourceResponse] = Field(description="数据源列表")
    count: int = Field(description="返回数量")


class ThemeQuotesRefreshResponse(BaseModel):
    """题材列表行情快刷响应。"""

    trade_date: date | None = Field(default=None, description="行情交易日")
    themes_updated: int = Field(description="更新题材数量")
    refreshed_at: datetime = Field(description="刷新完成时间")
