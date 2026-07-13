"""FastAPI 应用入口

创建和配置 FastAPI 应用实例。
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.api.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print("Starting TradingThemesGod API...")
    yield
    # 关闭时执行
    print("Shutting down TradingThemesGod API...")


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例"""
    settings = get_settings()

    app = FastAPI(
        title="TradingThemesGod API",
        description="股票题材与产业链分析平台 API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # 配置 CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(health_router, prefix="/api/v1")

    return app


# 创建应用实例
app = create_app()
