"""题材相关 Pydantic 模型

定义题材 API 的请求和响应数据结构。
"""

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class ThemeSearchParams(BaseModel):
    """题材列表查询参数"""

    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")
    sort_by: str = Field(default="heat_index", description="排序字段: heat_index/rise_fall_pct")
    sort_order: str = Field(default="desc", description="排序方向: asc/desc")
    category: str | None = Field(default=None, description="按分类筛选")
    tags: str | None = Field(default=None, description="按标签筛选（逗号分隔）")


class ThemeBrief(BaseModel):
    """题材简要信息（列表用）"""

    id: int = Field(description="题材ID")
    name: str = Field(description="题材名称")
    code: str = Field(description="题材代码")
    description: str | None = Field(default=None, description="题材描述")
    heat_index: Decimal = Field(description="热度指数")
    rise_fall_pct: Decimal = Field(description="涨跌幅(%)")
    stock_count: int = Field(description="关联股票数量")
    category: str | None = Field(default=None, description="题材分类")
    tags: list | dict | None = Field(default=None, description="标签列表")
    source: str | None = Field(default=None, description="数据来源")

    model_config = {"from_attributes": True}


class IndustryChainBrief(BaseModel):
    """产业链环节简要信息"""

    id: int = Field(description="产业链ID")
    level: str = Field(description="产业链层级: upstream/midstream/downstream")
    name: str = Field(description="环节名称")
    description: str | None = Field(default=None, description="环节描述")
    representative_companies: list | dict | None = Field(default=None, description="代表公司列表")
    sort_order: int = Field(description="排序顺序")

    model_config = {"from_attributes": True}


class ThemeListResponse(BaseModel):
    """题材列表响应"""

    items: list[ThemeBrief] = Field(description="题材列表")
    total: int = Field(description="总数")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页数量")
    total_pages: int = Field(description="总页数")


class ThemeDetailResponse(BaseModel):
    """题材详情响应"""

    id: int = Field(description="题材ID")
    name: str = Field(description="题材名称")
    code: str = Field(description="题材代码")
    description: str | None = Field(default=None, description="题材描述")
    heat_index: Decimal = Field(description="热度指数")
    rise_fall_pct: Decimal = Field(description="涨跌幅(%)")
    stock_count: int = Field(description="关联股票数量")
    category: str | None = Field(default=None, description="题材分类")
    tags: list | dict | None = Field(default=None, description="标签列表")
    source: str | None = Field(default=None, description="数据来源")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")
    industry_chains: dict[str, list[IndustryChainBrief]] = Field(
        description="产业链数据（按层级分组）"
    )

    model_config = {"from_attributes": True}


class ThemeRankingResponse(BaseModel):
    """题材排名响应"""

    items: list[ThemeBrief] = Field(description="题材列表")
    limit: int = Field(description="返回数量限制")


class ThemeCategoriesResponse(BaseModel):
    """题材分类列表响应"""

    categories: list[str] = Field(description="分类列表")
