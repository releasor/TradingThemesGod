"""FastAPI 应用入口

创建和配置 FastAPI 应用实例。
"""

import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.errors import router as errors_router
from app.api.health import router as health_router
from app.api.scraper import router as scraper_router
from app.api.stats import router as stats_router
from app.api.stock import router as stock_router
from app.api.theme import router as theme_router
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging

# 配置结构化日志
setup_logging()
logger = get_logger(__name__)

# 速率限制器
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("Starting TradingThemesGod API...")
    yield
    # 关闭时执行
    logger.info("Shutting down TradingThemesGod API...")


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例"""
    settings = get_settings()

    app = FastAPI(
        title="TradingThemesGod API",
        description="""## 股票题材与产业链分析平台 API

### 功能特性

- 📊 **题材管理** - 获取、搜索、筛选题材数据
- 📈 **题材排名** - 按热度指数获取热门题材排行
- 🏭 **产业链数据** - 获取题材的上中下游产业链结构
- 📰 **事件追踪** - 获取股票相关新闻和事件
- 🕷️ **数据采集** - 触发和管理爬虫任务

### 数据源

- 东方财富 - 题材概念和热度数据
- 同花顺 - 产业链数据
- 新浪财经 - 财经新闻和事件
- AKShare - 股票基础信息

### 技术栈

- **后端**: Python FastAPI + SQLAlchemy
- **数据库**: MySQL
- **爬虫**: httpx + BeautifulSoup
""",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=[
            {
                "name": "themes",
                "description": "题材相关接口 - 获取、搜索、筛选题材数据",
            },
            {
                "name": "stocks",
                "description": "股票相关接口 - 获取股票详情和事件",
            },
            {
                "name": "scraper",
                "description": "爬虫管理接口 - 触发和管理数据采集任务",
            },
            {
                "name": "health",
                "description": "健康检查接口 - 服务状态和数据库连接检查",
            },
            {
                "name": "errors",
                "description": "错误上报接口 - 接收前端错误日志",
            },
        ],
        lifespan=lifespan,
    )

    # 配置速率限制
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # 配置 CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 跳过日志记录的路径（健康检查和文档）
    _SKIP_LOG_PATHS = frozenset({
        "/api/v1/health", "/docs", "/redoc", "/openapi.json",
    })

    # 请求日志中间件
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """记录每个请求的方法、路径、状态码和耗时"""
        # 跳过健康检查和文档路径
        if request.url.path in _SKIP_LOG_PATHS:
            return await call_next(request)

        # 生成请求 ID
        request_id = str(uuid4())
        request.state.request_id = request_id

        start_time = time.monotonic()

        # 处理请求
        response = await call_next(request)

        # 将请求 ID 添加到响应头
        response.headers["X-Request-ID"] = request_id

        # 计算耗时
        duration_ms = (time.monotonic() - start_time) * 1000

        # 记录请求日志
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
            client=request.client.host if request.client else None,
            request_id=request_id,
        )

        return response

    # 注册路由
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(scraper_router, prefix="/api/v1")
    app.include_router(theme_router, prefix="/api/v1")
    app.include_router(stock_router, prefix="/api/v1")
    app.include_router(errors_router, prefix="/api/v1")
    app.include_router(stats_router, prefix="/api/v1")

    # 全局异常处理器
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """捕获所有未处理的异常，返回统一错误响应"""
        request_id = str(uuid4())

        logger.error(
            "unhandled_exception",
            exc_type=type(exc).__name__,
            exc_message=str(exc),
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else None,
            request_id=request_id,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": "服务器内部错误，请稍后重试",
                "detail": None,
                "request_id": request_id,
            },
        )

    return app


# 创建应用实例
app = create_app()
