"""爬虫调度器单元测试"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.scrapers.base import BaseScraper
from app.scrapers.registry import ScraperRegistry
from app.scrapers.scheduler import ScraperScheduler


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


@pytest.mark.asyncio
async def test_scheduler_periodic_collection_runs_immediately(registry):
    """周期采集启动后应立即执行一次"""
    scheduler = ScraperScheduler(registry=registry)
    scheduler.run = AsyncMock(return_value=1)

    first_task = scheduler.start_periodic("test", interval_seconds=60)
    second_task = scheduler.start_periodic("test", interval_seconds=60)
    await asyncio.sleep(0)

    assert first_task is second_task
    scheduler.run.assert_awaited_once_with("test")

    await scheduler.stop_periodic("test")
    assert first_task.cancelled()


@pytest.mark.asyncio
async def test_scheduler_periodic_collection_skips_overlapping_run(registry):
    """上一次采集未结束时不应重复启动同一数据源"""
    scheduler = ScraperScheduler(registry=registry)
    scheduler.run = AsyncMock(return_value=1)
    scheduler.is_running = MagicMock(return_value=True)

    scheduler.start_periodic("test", interval_seconds=60)
    await asyncio.sleep(0)

    scheduler.run.assert_not_awaited()
    await scheduler.stop_periodic("test")


@pytest.mark.asyncio
async def test_scheduler_run_rejects_when_source_already_running(registry):
    """手动触发时若同数据源已在运行则拒绝。"""
    scheduler = ScraperScheduler(registry=registry)
    scheduler.is_running = MagicMock(return_value=True)

    with pytest.raises(ValueError, match="正在运行中"):
        await scheduler.run("test")
