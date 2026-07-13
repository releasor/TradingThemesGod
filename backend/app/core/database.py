"""数据库连接模块

提供 SQLAlchemy 异步引擎和会话管理。
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import get_settings

settings = get_settings()

# 创建异步引擎
engine = create_async_engine(
    settings.database_url,
    echo=settings.APP_DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """获取数据库会话（用于 FastAPI 依赖注入）"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
