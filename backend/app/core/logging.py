"""结构化日志配置

使用 structlog 提供结构化日志，便于日志收集和分析。
"""

import logging
import sys

import structlog

from app.core.config import get_settings


def setup_logging() -> None:
    """配置 structlog 结构化日志

    根据环境自动选择日志格式：
    - 开发环境：彩色控制台输出，便于阅读
    - 生产环境：JSON 格式，便于日志收集
    """
    settings = get_settings()

    # 配置标准库日志
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if settings.APP_DEBUG else logging.INFO,
    )

    # 共同的处理器链
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.APP_DEBUG:
        # 开发环境：彩色控制台输出
        structlog.configure(
            processors=[
                *shared_processors,
                structlog.dev.ConsoleRenderer(colors=True),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # 生产环境：JSON 格式
        structlog.configure(
            processors=[
                *shared_processors,
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """获取结构化日志器

    Args:
        name: 日志器名称，通常为模块名

    Returns:
        绑定的结构化日志器
    """
    return structlog.get_logger(name)
