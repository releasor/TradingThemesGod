"""前端错误上报 API 端点

接收前端错误日志，记录到日志系统。
"""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.logging import get_logger

# 速率限制器
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/errors", tags=["errors"])
logger = get_logger(__name__)


class FrontendError(BaseModel):
    """前端错误数据"""

    message: str
    stack: Optional[str] = None
    componentStack: Optional[str] = None
    url: Optional[str] = None
    userAgent: Optional[str] = None
    timestamp: Optional[str] = None


@router.post("")
@limiter.limit("30/minute")  # 每分钟最多 30 次错误上报
async def report_frontend_error(error: FrontendError, request: Request):
    """接收前端错误上报

    Args:
        error: 前端错误数据
        request: FastAPI 请求对象

    Returns:
        确认响应
    """
    client_ip = request.client.host if request.client else "unknown"

    logger.error(
        "frontend_error",
        message=error.message,
        stack=error.stack,
        component_stack=error.componentStack,
        url=error.url,
        user_agent=error.userAgent,
        client_ip=client_ip,
        timestamp=error.timestamp or datetime.now(timezone.utc).isoformat(),
    )

    return {"status": "ok", "message": "错误已记录"}
