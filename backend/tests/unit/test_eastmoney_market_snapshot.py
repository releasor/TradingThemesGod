"""东方财富采集后的题材市场快照联动测试。"""

from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from app.scrapers.eastmoney import EastMoneyScraper


@pytest.mark.asyncio
async def test_refresh_market_snapshots_delegates_to_market_service():
    session = AsyncMock()
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=session)
    context.__aexit__ = AsyncMock(return_value=False)
    service = MagicMock()
    service.refresh_all = AsyncMock(return_value=2)

    with (
        patch("app.scrapers.eastmoney.AsyncSessionLocal", return_value=context),
        patch("app.scrapers.eastmoney.ThemeMarketService", return_value=service),
    ):
        await EastMoneyScraper()._refresh_market_snapshots(date(2026, 7, 20))

    service.refresh_all.assert_awaited_once_with(date(2026, 7, 20))


def test_extract_trade_date_uses_latest_quote_timestamp():
    earlier = int(
        datetime(2026, 7, 16, 15, tzinfo=ZoneInfo("Asia/Shanghai")).timestamp()
    )
    latest = int(
        datetime(2026, 7, 17, 15, tzinfo=ZoneInfo("Asia/Shanghai")).timestamp()
    )

    result = EastMoneyScraper._extract_trade_date(
        {"data": {"diff": [{"f124": earlier}, {"f124": latest}]}}
    )

    assert result == date(2026, 7, 17)


@pytest.mark.asyncio
async def test_run_refreshes_snapshot_for_quote_trade_date_not_server_date():
    scraper = EastMoneyScraper()
    quote_time = int(
        datetime(2026, 7, 17, 15, tzinfo=ZoneInfo("Asia/Shanghai")).timestamp()
    )
    theme_payload = {
        "data": {"total": 1, "diff": [{"f12": "BK0001", "f14": "测试题材"}]}
    }
    stock_payload = {
        "data": {
            "total": 1,
            "diff": [
                {
                    "f2": 10,
                    "f3": 1,
                    "f12": "000001",
                    "f14": "测试股票",
                    "f124": quote_time,
                }
            ],
        }
    }
    scraper.fetch_all_pages = AsyncMock(side_effect=[theme_payload, stock_payload])
    scraper._save_themes = AsyncMock(return_value=1)
    scraper._save_theme_stocks = AsyncMock(return_value=1)
    scraper._refresh_market_snapshots = AsyncMock(return_value=1)

    await scraper.run()

    scraper._refresh_market_snapshots.assert_awaited_once_with(date(2026, 7, 17))
