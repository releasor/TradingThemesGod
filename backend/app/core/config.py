"""应用配置模块

使用 Pydantic Settings 管理配置，支持环境变量和 .env 文件。
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置类"""

    # 应用配置
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_ENV: str = "development"
    APP_DEBUG: bool = True

    # 数据库配置
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "trading_themes"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""

    # CORS 配置
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    @property
    def database_url(self) -> str:
        """构建数据库连接 URL"""
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def database_url_sync(self) -> str:
        """构建同步数据库连接 URL（用于 Alembic）"""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
