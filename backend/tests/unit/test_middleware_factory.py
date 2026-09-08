"""middleware_factory 单元测试。"""

from app.core.config import Settings
from app.scrapers.eastmoney import EastMoneyScraper
from app.scrapers.middleware_factory import (
    build_anti_scraping_middleware,
    create_scraper_from_settings,
)
from app.scrapers.registry import scraper_registry


def test_build_middleware_proxy_disabled(monkeypatch):
    settings = Settings(PROXY_ENABLED=False, PROXY_URL="http://proxy:8080", _env_file=None)
    monkeypatch.setattr(
        "app.scrapers.middleware_factory.get_settings",
        lambda: settings,
    )
    middleware = build_anti_scraping_middleware()
    assert middleware.proxy_url is None
    assert middleware.min_interval == 1.0
    assert middleware.max_interval == 3.0


def test_build_middleware_proxy_enabled(monkeypatch):
    settings = Settings(
        PROXY_ENABLED=True,
        PROXY_URL="http://proxy:8080",
        _env_file=None,
    )
    monkeypatch.setattr(
        "app.scrapers.middleware_factory.get_settings",
        lambda: settings,
    )
    middleware = build_anti_scraping_middleware(
        min_interval=0.2,
        max_interval=0.6,
        max_retries=1,
    )
    assert middleware.proxy_url == "http://proxy:8080"
    assert middleware.min_interval == 0.2
    assert middleware.max_interval == 0.6
    assert middleware.max_retries == 1


def test_create_scraper_from_settings_eastmoney(monkeypatch):
    settings = Settings(PROXY_ENABLED=True, PROXY_URL="http://p", _env_file=None)
    monkeypatch.setattr(
        "app.scrapers.middleware_factory.get_settings",
        lambda: settings,
    )
    scraper_registry.register("eastmoney", EastMoneyScraper)
    scraper = create_scraper_from_settings("eastmoney")
    assert isinstance(scraper, EastMoneyScraper)
    assert scraper.middleware.proxy_url == "http://p"
