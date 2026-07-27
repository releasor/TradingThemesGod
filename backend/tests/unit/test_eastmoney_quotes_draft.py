"""东方财富题材行情草稿采集（仅采集不落库）单元测试。"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.scrapers.eastmoney import EastMoneyScraper


@pytest.mark.asyncio
async def test_collect_theme_quotes_returns_data_without_saving():
    scraper = EastMoneyScraper()
    quote_time = 1721203200  # 任意有效时间戳，具体日期由 _extract_trade_date 解析
    theme_payload = {
        "data": {
            "diff": [
                {
                    "f3": 2.5,
                    "f8": 85.6,
                    "f12": "BK0XXX",
                    "f14": "锂电池",
                    "f104": 50,
                    "f124": quote_time,
                }
            ]
        }
    }
    scraper.fetch_all_pages = AsyncMock(return_value=theme_payload)
    scraper._save_themes = AsyncMock(return_value=1)

    trade_date, themes = await scraper.collect_theme_quotes()

    assert isinstance(trade_date, date)
    assert len(themes) == 1
    assert themes[0]["code"] == "BK0XXX"
    assert themes[0]["name"] == "锂电池"
    assert themes[0]["heat_index"] == Decimal("85.6")
    assert themes[0]["rise_fall_pct"] == Decimal("2.5")
    scraper._save_themes.assert_not_called()


@pytest.mark.asyncio
async def test_refresh_theme_quotes_still_saves():
    scraper = EastMoneyScraper()
    themes = [
        {
            "code": "BK0XXX",
            "name": "锂电池",
            "heat_index": Decimal("85.6"),
            "rise_fall_pct": Decimal("2.5"),
            "stock_count": 50,
        }
    ]
    scraper.collect_theme_quotes = AsyncMock(return_value=(date(2026, 7, 27), themes))
    scraper._save_themes = AsyncMock(return_value=1)

    trade_date, count = await scraper.refresh_theme_quotes()

    assert trade_date == date(2026, 7, 27)
    assert count == 1
    scraper._save_themes.assert_awaited_once_with(themes)
