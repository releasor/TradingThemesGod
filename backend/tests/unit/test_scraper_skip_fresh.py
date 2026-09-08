"""周期采集 skip-if-fresh 与仓库方法测试。"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.scrapers.base import BaseScraper
from app.scrapers.registry import ScraperRegistry
from app.scrapers.scheduler import ScraperScheduler, should_skip_periodic_run


class MockScraper(BaseScraper):
    source_name = "test"

    def parse(self, html: str) -> list[dict]:
        return []

    async def save(self, data: list[dict]) -> int:
        return 0


@pytest.fixture
def registry():
    reg = ScraperRegistry()
    reg.register("test", MockScraper)
    return reg


def test_should_skip_periodic_run_fresh():
    now = datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)
    last = now - timedelta(hours=1)
    assert should_skip_periodic_run(last, now, 21600) is True


def test_should_skip_periodic_run_stale():
    now = datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)
    last = now - timedelta(hours=7)
    assert should_skip_periodic_run(last, now, 21600) is False


def test_should_skip_periodic_run_none():
    now = datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)
    assert should_skip_periodic_run(None, now, 21600) is False
    assert should_skip_periodic_run(now, now, 0) is False


@pytest.mark.asyncio
async def test_periodic_skips_when_fresh(registry):
    scheduler = ScraperScheduler(registry=registry)
    scheduler.run = AsyncMock(return_value=1)
    scheduler._should_skip_periodic = AsyncMock(return_value=True)

    scheduler.start_periodic("test", interval_seconds=60)
    await __import__("asyncio").sleep(0)

    scheduler.run.assert_not_awaited()
    await scheduler.stop_periodic("test")


@pytest.mark.asyncio
async def test_periodic_runs_when_not_fresh(registry):
    scheduler = ScraperScheduler(registry=registry)
    scheduler.run = AsyncMock(return_value=1)
    scheduler._should_skip_periodic = AsyncMock(return_value=False)

    scheduler.start_periodic("test", interval_seconds=60)
    await __import__("asyncio").sleep(0)

    scheduler.run.assert_awaited_once_with("test")
    await scheduler.stop_periodic("test")


@pytest.mark.asyncio
async def test_get_latest_completed_orders_by_finished_at():
    from app.repositories.scraper_run import ScraperRunRepository

    session = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = MagicMock(id=9)
    session.execute = AsyncMock(return_value=result)
    repo = ScraperRunRepository(session)
    run = await repo.get_latest_completed("eastmoney")
    assert run.id == 9
    session.execute.assert_awaited()
