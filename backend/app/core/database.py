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
    pool_timeout=30,  # 连接池超时时间（秒）
    pool_recycle=3600,  # 连接回收时间（秒）
    connect_args={
        "connect_timeout": 10,  # 连接超时时间（秒）
        "command_timeout": 30,  # 命令超时时间（秒）
    },
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """获取数据库会话（用于 FastAPI 依赖注入）

    注意：不再自动 commit。写操作需要在 service/repository 层显式调用 await session.commit()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
