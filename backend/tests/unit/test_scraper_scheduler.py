"""爬虫调度器单元测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.scrapers.scheduler import ScraperScheduler
from app.scrapers.registry import ScraperRegistry
from app.scrapers.base import BaseScraper


class MockScraper(BaseScraper):
    """测试用爬虫"""

    source_name = "test"

    def parse(self, html: str) -> list[dict]:
        return [{"title": "test"}]

    async def save(self, data: list[dict]) -> int:
        return len(data)


@pytest.fixture
def registry():
    """创建带测试爬虫的注册表"""
    reg = ScraperRegistry()
    reg.register("test", MockScraper)
    return reg


@pytest.mark.asyncio
async def test_scheduler_run_unregistered_source():
    """测试运行未注册的数据源"""
    scheduler = ScraperScheduler(registry=ScraperRegistry())

    with pytest.raises(ValueError, match="未注册的数据源"):
        await scheduler.run("nonexistent", {"url": "http://example.com"})


@pytest.mark.asyncio
async def test_scheduler_list_sources(registry):
    """测试列出已注册数据源"""
    scheduler = ScraperScheduler(registry=registry)

    sources = scheduler.registry.list_sources()
    assert "test" in sources


@pytest.mark.asyncio
async def test_scraper_registry_register():
    """测试注册爬虫"""
    reg = ScraperRegistry()
    reg.register("test", MockScraper)

    assert reg.get("test") == MockScraper
    assert reg.get("nonexistent") is None


@pytest.mark.asyncio
async def test_scraper_registry_invalid_class():
    """测试注册无效类"""
    reg = ScraperRegistry()

    with pytest.raises(TypeError):
        reg.register("test", str)
