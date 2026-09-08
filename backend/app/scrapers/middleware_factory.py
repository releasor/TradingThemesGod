"""按应用配置构建反爬中间件与爬虫实例。"""

from __future__ import annotations

from app.core.config import get_settings
from app.scrapers.anti_scraping import AntiScrapingMiddleware
from app.scrapers.base import BaseScraper
from app.scrapers.registry import scraper_registry


def build_anti_scraping_middleware(
    *,
    min_interval: float | None = None,
    max_interval: float | None = None,
    max_retries: int | None = None,
) -> AntiScrapingMiddleware:
    """从 Settings 读取代理，并允许覆盖间隔/重试（行情路径可更紧）。"""
    settings = get_settings()
    proxy_url = settings.PROXY_URL if settings.PROXY_ENABLED else None
    return AntiScrapingMiddleware(
        proxy_url=proxy_url or None,
        min_interval=1.0 if min_interval is None else min_interval,
        max_interval=3.0 if max_interval is None else max_interval,
        max_retries=3 if max_retries is None else max_retries,
    )


def create_scraper_from_settings(
    source: str,
    *,
    min_interval: float | None = None,
    max_interval: float | None = None,
    max_retries: int | None = None,
) -> BaseScraper:
    """按注册表创建爬虫，并注入 settings 感知的中间件。"""
    scraper_cls = scraper_registry.get(source)
    if scraper_cls is None:
        raise ValueError(f"未注册的数据源: {source}")
    middleware = build_anti_scraping_middleware(
        min_interval=min_interval,
        max_interval=max_interval,
        max_retries=max_retries,
    )
    return scraper_cls(middleware=middleware)
