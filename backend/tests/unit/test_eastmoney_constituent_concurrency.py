"""东财 collect_full 成分股并发上限测试。"""

import asyncio
from datetime import date
from unittest.mock import AsyncMock

import pytest

from app.core.config import Settings
from app.scrapers.anti_scraping import AntiScrapingMiddleware
from app.scrapers.eastmoney import EastMoneyScraper


@pytest.mark.asyncio
async def test_collect_full_respects_constituent_concurrency(monkeypatch):
    settings = Settings(SCRAPER_EM_CONSTITUENT_CONCURRENCY=2, _env_file=None)
    monkeypatch.setattr("app.scrapers.eastmoney.get_settings", lambda: settings)

    scraper = EastMoneyScraper(middleware=AntiScrapingMiddleware(min_interval=0, max_interval=0))
    themes = [{"code": f"BK{i:04d}", "name": f"T{i}"} for i in range(6)]
    monkeypatch.setattr(
        scraper,
        "parse_theme_list",
        lambda _data: themes,
    )

    in_flight = 0
    max_in_flight = 0
    lock = asyncio.Lock()

    async def fake_fetch_all_pages(_url, params):
        nonlocal in_flight, max_in_flight
        fs = params.get("fs", "")
        if fs.startswith("b:"):
            async with lock:
                in_flight += 1
                max_in_flight = max(max_in_flight, in_flight)
            await asyncio.sleep(0.05)
            async with lock:
                in_flight -= 1
            return {"data": {"diff": []}}
        return {"data": {"diff": [{"f12": "BK0001", "f14": "x"}]}}

    scraper.fetch_all_pages = AsyncMock(side_effect=fake_fetch_all_pages)
    monkeypatch.setattr(scraper, "parse_theme_stocks", lambda _data, _code: [])
    monkeypatch.setattr(scraper, "_extract_trade_date", lambda _data: date(2026, 9, 8))

    # bypass concept cache path by ensuring fetch goes through our mock
    from app.scrapers import concept_list_cache

    concept_list_cache.clear()
    try:
        draft = await scraper.collect_full()
        assert len(draft.themes) == 6
        assert max_in_flight <= 2
    finally:
        concept_list_cache.clear()
