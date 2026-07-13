"""健康检查端点

提供服务状态和数据库连接状态检查。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db, engine

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """健康检查端点

    返回服务状态、数据库连接状态和连接池信息。
    """
    try:
        # 检查数据库连接
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    # 获取连接池状态
    pool = engine.pool
    pool_status = {
        "size": pool.size(),  # 连接池大小
        "checked_in": pool.checkedin(),  # 空闲连接数
        "checked_out": pool.checkedout(),  # 活跃连接数
        "overflow": pool.overflow(),  # 溢出连接数
    }

    # 根据数据库状态决定整体健康状态
    overall_status = "healthy" if db_status == "connected" else "unhealthy"

    return {
        "status": overall_status,
        "database": db_status,
        "pool": pool_status,
    }
