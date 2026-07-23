"""爬虫数据源目录测试。"""

from app.domain.scraper_sources import (
    get_default_dashboard_source,
    list_registered_scraper_sources,
)
from app.scrapers.registry import register_default_scrapers


def test_list_registered_scraper_sources_includes_catalog_entries():
    register_default_scrapers()
    sources = list_registered_scraper_sources()
    source_ids = {item.id for item in sources}
    assert source_ids == {"eastmoney", "ths", "akshare", "sina"}


def test_list_dashboard_scraper_sources_filters_specialized_sources():
    register_default_scrapers()
    sources = list_registered_scraper_sources(dashboard_only=True)
    assert [item.id for item in sources] == ["eastmoney", "akshare"]


def test_get_default_dashboard_source_prefers_eastmoney():
    register_default_scrapers()
    assert get_default_dashboard_source() == "eastmoney"
