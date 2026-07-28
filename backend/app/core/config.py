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
    # 复盘日报盘后调度（默认关闭；首开 ensure 已够用，勿在 lifespan 无条件启动）
    REVIEW_REPORT_SCHEDULER_ENABLED: bool = False

    # 雪球公开信息访问配置（可选）
    XUEQIU_COOKIE: str = ""

    # Tushare Pro（可选；未启用或未配置 token 时不参与全量竞速）
    TUSHARE_ENABLED: bool = False
    TUSHARE_TOKEN: str = ""
    # 自定义 Pro HTTP 地址，留空则用官方默认
    TUSHARE_API_URL: str = ""
    # 概念列表接口尝试顺序（逗号分隔）：concept | ths_index | dc_index
    TUSHARE_CONCEPT_APIS: str = "concept,ths_index,dc_index"
    # concept(src=...) 参数，常见 ts / ths
    TUSHARE_CONCEPT_SRC: str = "ts"
    # ths_index(type=...) 参数，N=概念
    TUSHARE_THS_INDEX_TYPE: str = "N"
    TUSHARE_THS_INDEX_EXCHANGE: str = "A"
    TUSHARE_MAX_RETRIES: int = 3

    # JWT 认证
    JWT_SECRET: str = "change-me-in-production"
    JWT_EXPIRE_DAYS: int = 7

    def tushare_concept_api_list(self) -> list[str]:
        """解析概念接口尝试顺序。"""
        raw = (self.TUSHARE_CONCEPT_APIS or "").strip()
        if not raw:
            return ["concept", "ths_index", "dc_index"]
        return [part.strip().lower() for part in raw.split(",") if part.strip()]

    def tushare_ready(self) -> bool:
        """是否启用且已配置 token。"""
        return bool(self.TUSHARE_ENABLED) and bool((self.TUSHARE_TOKEN or "").strip())

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
