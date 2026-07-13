"""健康检查端点

提供服务状态和数据库连接状态检查。
"""

import time
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db, engine
from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """健康检查端点

    返回服务状态、数据库连接状态和连接池信息。
    数据库异常时返回 HTTP 503。
    """
    settings = get_settings()
    start = time.monotonic()

    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    duration_ms = round((time.monotonic() - start) * 1000, 2)

    # 获取连接池状态
    pool = engine.pool
    pool_status = {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
    }

    overall_status = "healthy" if db_status == "connected" else "unhealthy"

    body = {
        "status": overall_status,
        "version": settings.APP_ENV,
        "database": db_status,
        "response_time_ms": duration_ms,
        "pool": pool_status,
    }

    if overall_status == "unhealthy":
        return JSONResponse(status_code=503, content=body)

    return body
