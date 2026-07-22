"""应用配置模块

使用 Pydantic Settings 管理配置，支持环境变量和 .env 文件。
"""

from functools import lru_cache

from pydantic_settings import BaseSettings
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    """应用配置类"""

    # 应用配置
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_ENV: str = "development"
    APP_DEBUG: bool = False

    # 数据库配置
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "trading_themes"
    DB_USER: str = "root"
    DB_PASSWORD: str = ""

    # CORS 配置
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # 代理配置（可选）
    PROXY_ENABLED: bool = False
    PROXY_URL: str = ""

    # 自动采集配置
    SCRAPER_AUTO_ENABLED: bool = True
    SCRAPER_INTERVAL_SECONDS: int = 21600
    THEME_INSIGHT_AUTO_ENABLED: bool = True
    THEME_INSIGHT_INTERVAL_SECONDS: int = 3600
    THEME_INSIGHT_BATCH_SIZE: int = 10
    THEME_PROFILE_MAX_AGE_DAYS: int = 7

    # 雪球公开信息访问配置（可选）
    XUEQIU_COOKIE: str = ""

    @property
    def database_url(self) -> str:
        """构建数据库连接 URL"""
        url = URL.create(
            drivername="mysql+asyncmy",
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
            query={"charset": "utf8mb4"},
        )
        return url.render_as_string(hide_password=False)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
