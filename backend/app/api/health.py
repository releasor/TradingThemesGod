"""健康检查端点

提供服务状态和数据库连接状态检查。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """健康检查端点

    返回服务状态和数据库连接状态。
    """
    try:
        # 检查数据库连接
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    # 根据数据库状态决定整体健康状态
    overall_status = "healthy" if db_status == "connected" else "unhealthy"

    return {
        "status": overall_status,
        "database": db_status,
    }
