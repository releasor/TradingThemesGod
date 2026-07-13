"""通用响应模型

提供统一的 API 响应格式。
"""

from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field
from uuid import uuid4

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应格式

    所有 API 端点都应使用此格式返回数据。
    """

    code: int = Field(default=200, description="响应状态码")
    message: str = Field(default="success", description="响应消息")
    data: T | None = Field(default=None, description="响应数据")
    request_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="请求ID，用于问题追踪"
    )


class ErrorResponse(BaseModel):
    """错误响应格式"""

    code: int = Field(description="错误状态码")
    message: str = Field(description="错误消息")
    detail: Any | None = Field(default=None, description="错误详情")
    request_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="请求ID，用于问题追踪"
    )


class PaginationMeta(BaseModel):
    """分页元数据"""

    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页数量")
    total: int = Field(description="总记录数")
    total_pages: int = Field(description="总页数")


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应格式"""

    items: list[T] = Field(description="数据列表")
    total: int = Field(description="总记录数")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页数量")
    total_pages: int = Field(description="总页数")
