"""爬虫模块

提供爬虫基类、反爬虫中间件、注册表和调度器。
"""

from app.scrapers.base import BaseScraper
from app.scrapers.anti_scraping import AntiScrapingMiddleware
from app.scrapers.registry import ScraperRegistry, scraper_registry
from app.scrapers.scheduler import ScraperScheduler, scraper_scheduler

__all__ = [
    "BaseScraper",
    "AntiScrapingMiddleware",
    "ScraperRegistry",
    "scraper_registry",
    "ScraperScheduler",
    "scraper_scheduler",
]
