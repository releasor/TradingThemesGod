"""通用 Pydantic 模型

提供跨模块共用的响应模型和工具函数。
"""

from math import ceil
from typing import Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


def calculate_total_pages(total: int, page_size: int) -> int:
    """计算总页数

    Args:
        total: 总记录数
        page_size: 每页数量

    Returns:
        总页数（total 为 0 时返回 0）
    """
    return ceil(total / page_size) if total > 0 else 0


__all__ = [
    "calculate_total_pages",
]
