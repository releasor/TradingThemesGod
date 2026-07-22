import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.api import stats as stats_api
from app.main import create_app, theme_insight_scheduler
from app.schemas.scraper import ScraperRunResponse
from app.scrapers.anti_scraping import AntiScrapingMiddleware
from app.scrapers.eastmoney import DEFAULT_PARAMS, EastMoneyScraper
from app.scrapers.registry import scraper_registry


@pytest.mark.asyncio
async def test_app_lifespan_registers_default_scrapers():
    original_scrapers = scraper_registry._scrapers.copy()
    scraper_registry._scrapers.clear()
    app = create_app()

    try:
        async with app.router.lifespan_context(app):
            assert "eastmoney" in scraper_registry.list_sources()
    finally:
        scraper_registry._scrapers.clear()
        scraper_registry._scrapers.update(original_scrapers)


@pytest.mark.asyncio
async def test_app_lifespan_starts_and_stops_auto_collection(monkeypatch):
    """开启自动采集时，应用生命周期应负责启动和停止调度任务"""
    app = create_app()
    settings = MagicMock(
        SCRAPER_AUTO_ENABLED=True,
        SCRAPER_INTERVAL_SECONDS=3600,
    )
    start_periodic = MagicMock()
    run = AsyncMock(return_value=1)
    stop_periodic = AsyncMock()

    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    monkeypatch.setattr(
        "app.main.scraper_scheduler.start_periodic",
        start_periodic,
    )
    monkeypatch.setattr(
        "app.main.scraper_scheduler.stop_periodic",
        stop_periodic,
    )
    monkeypatch.setattr("app.main.scraper_scheduler.run", run)

    async with app.router.lifespan_context(app):
        start_periodic.assert_called_once_with(
            "eastmoney",
            interval_seconds=3600,
        )

    stop_periodic.assert_awaited_once_with("eastmoney")
    run.assert_not_awaited()


@pytest.mark.asyncio
async def test_app_lifespan_starts_and_stops_theme_insight_periodic(monkeypatch):
    """开启题材研究刷新时，应用生命周期应负责启动和停止调度任务"""
    app = create_app()
    settings = MagicMock(
        SCRAPER_AUTO_ENABLED=False,
        THEME_INSIGHT_AUTO_ENABLED=True,
        THEME_INSIGHT_INTERVAL_SECONDS=3600,
        THEME_INSIGHT_BATCH_SIZE=10,
        THEME_PROFILE_MAX_AGE_DAYS=7,
    )
    start = MagicMock()
    stop = AsyncMock()

    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    monkeypatch.setattr("app.main.theme_insight_scheduler.start", start)
    monkeypatch.setattr("app.main.theme_insight_scheduler.stop", stop)

    async with app.router.lifespan_context(app):
        start.assert_called_once_with(3600)

    assert theme_insight_scheduler.batch_size == 10
    assert theme_insight_scheduler.profile_max_age_days == 7
    stop.assert_awaited_once()


def test_scraper_run_response_maps_model_id_to_run_id():
    class Run:
        id = 42
        source = "eastmoney"
        status = "running"
        started_at = datetime.now(UTC)
        finished_at = None
        items_scraped = 0
        error_message = None

    response = ScraperRunResponse.model_validate(Run())

    assert response.run_id == 42


def test_eastmoney_parser_handles_null_data():
    scraper = EastMoneyScraper()

    assert scraper.parse_theme_list({"rc": 102, "data": None}) == []
    assert scraper.parse_theme_stocks({"rc": 102, "data": None}, "BK0877") == []


def test_eastmoney_uses_supported_page_size():
    assert DEFAULT_PARAMS["pz"] == "5"


def test_eastmoney_includes_page_number():
    assert DEFAULT_PARAMS["pn"] == "1"


@pytest.mark.asyncio
async def test_stats_queries_do_not_share_a_session_concurrently(monkeypatch):
    active_queries = 0

    async def query(_db):
        nonlocal active_queries
        active_queries += 1
        assert active_queries == 1
        await asyncio.sleep(0)
        active_queries -= 1
        return 0

    async def query_categories(_db):
        await query(_db)
        return []

    async def query_scraper(_db):
        await query(_db)
        return None

    monkeypatch.setattr(stats_api, "_query_theme_count", query)
    monkeypatch.setattr(stats_api, "_query_stock_count", query)
    monkeypatch.setattr(stats_api, "_query_event_count", query)
    monkeypatch.setattr(stats_api, "_query_chain_count", query)
    monkeypatch.setattr(stats_api, "_query_last_scraper", query_scraper)
    monkeypatch.setattr(stats_api, "_query_category_stats", query_categories)

    response = await stats_api.get_stats(object())

    assert response["themes"]["total"] == 0


@pytest.mark.asyncio
async def test_middleware_retries_remote_protocol_error():
    middleware = AntiScrapingMiddleware(min_interval=0, max_interval=0, max_retries=1)
    response = MagicMock(status_code=200)
    client = AsyncMock()
    client.request = AsyncMock(
        side_effect=[httpx.RemoteProtocolError("disconnected"), response]
    )

    with (
        patch.object(middleware, "_get_client", return_value=client),
        patch("app.scrapers.anti_scraping.asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await middleware.get("https://example.com")

    assert result is response
    assert client.request.call_count == 2
