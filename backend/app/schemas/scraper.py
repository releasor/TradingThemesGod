"""爬虫相关 Pydantic 模型

定义 API 请求和响应的数据结构。
"""

from datetime import datetime
from pydantic import BaseModel, Field


class ScraperRunRequest(BaseModel):
    """爬虫运行请求"""

    params: dict = Field(default_factory=dict, description="爬虫参数")


class ScraperRunResponse(BaseModel):
    """爬虫运行响应"""

    run_id: int = Field(description="运行记录 ID")
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
