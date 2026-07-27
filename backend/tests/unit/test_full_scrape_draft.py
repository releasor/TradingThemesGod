"""全量爬虫 collect_full / commit_full 单元测试。"""

import asyncio
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest

from app.scrapers.akshare import AKShareScraper
from app.scrapers.draft_types import FullScrapeDraft
from app.scrapers.eastmoney import EastMoneyScraper


@pytest.fixture
def eastmoney_scraper():
    return EastMoneyScraper()


@pytest.fixture
def theme_payload():
    return {
        "data": {
            "diff": [
                {
                    "f3": 2.5,
                    "f8": 85.6,
                    "f12": "BK0XXX",
                    "f14": "锂电池",
                    "f104": 50,
                    "f124": 1721203200,
                },
                {
                    "f3": -1.2,
                    "f8": 92.3,
                    "f12": "BK0YYY",
                    "f14": "人工智能",
                    "f104": 30,
                    "f124": 1721203200,
                },
            ]
        }
    }


@pytest.fixture
def stocks_payload():
    return {
        "data": {
            "diff": [
                {
                    "f2": 15.68,
                    "f3": 3.2,
                    "f12": "000001",
                    "f14": "平安银行",
                    "f124": 1721203200,
                }
            ]
        }
    }


class TestEastMoneyCollectCommit:
    @pytest.mark.asyncio
    async def test_collect_full_does_not_save(
        self, eastmoney_scraper, theme_payload, stocks_payload
    ):
        eastmoney_scraper.fetch_all_pages = AsyncMock(
            side_effect=[theme_payload, stocks_payload, stocks_payload]
        )
        eastmoney_scraper._save_themes = AsyncMock(return_value=2)
        eastmoney_scraper._save_theme_stocks = AsyncMock(return_value=1)

        draft = await eastmoney_scraper.collect_full()

        assert draft.source == "eastmoney"
        assert len(draft.themes) == 2
        assert "BK0XXX" in draft.stocks_by_code
        assert "BK0YYY" in draft.stocks_by_code
        assert isinstance(draft.trade_date, date)
        eastmoney_scraper._save_themes.assert_not_called()
        eastmoney_scraper._save_theme_stocks.assert_not_called()

    @pytest.mark.asyncio
    async def test_commit_full_calls_saves(self, eastmoney_scraper):
        draft = FullScrapeDraft(
            source="eastmoney",
            trade_date=date(2024, 7, 17),
            themes=[
                {
                    "name": "锂电池",
                    "code": "BK0XXX",
                    "heat_index": Decimal("85.6"),
                    "rise_fall_pct": Decimal("2.5"),
                    "stock_count": 50,
                    "category": "新能源",
                    "source": "eastmoney",
                }
            ],
            stocks_by_code={
                "BK0XXX": [
                    {
                        "code": "000001",
                        "name": "平安银行",
                        "rise_fall_pct": Decimal("3.2"),
                        "current_price": Decimal("15.68"),
                    }
                ]
            },
        )
        eastmoney_scraper._save_themes = AsyncMock(return_value=1)
        eastmoney_scraper._save_theme_stocks = AsyncMock(return_value=1)
        eastmoney_scraper._refresh_market_snapshots = AsyncMock(return_value=1)

        count = await eastmoney_scraper.commit_full(draft)

        assert count == 2
        eastmoney_scraper._save_themes.assert_awaited_once_with(draft.themes)
        eastmoney_scraper._save_theme_stocks.assert_awaited_once_with(
            "BK0XXX", draft.stocks_by_code["BK0XXX"]
        )
        eastmoney_scraper._refresh_market_snapshots.assert_awaited_once_with(
            date(2024, 7, 17)
        )

    @pytest.mark.asyncio
    async def test_collect_full_cancel_mid_loop_raises(
        self, eastmoney_scraper, theme_payload, stocks_payload
    ):
        cancel = asyncio.Event()
        call_count = 0

        async def fetch_side_effect(*_args, **_kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return theme_payload
            cancel.set()
            return stocks_payload

        eastmoney_scraper.fetch_all_pages = AsyncMock(side_effect=fetch_side_effect)
        eastmoney_scraper._save_themes = AsyncMock()
        eastmoney_scraper._save_theme_stocks = AsyncMock()

        with pytest.raises(asyncio.CancelledError):
            await eastmoney_scraper.collect_full(cancel=cancel)

        eastmoney_scraper._save_themes.assert_not_called()
        eastmoney_scraper._save_theme_stocks.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_uses_collect_then_commit(
        self, eastmoney_scraper, theme_payload, stocks_payload
    ):
        eastmoney_scraper.fetch_all_pages = AsyncMock(
            side_effect=[theme_payload, stocks_payload, stocks_payload]
        )
        eastmoney_scraper._save_themes = AsyncMock(return_value=2)
        eastmoney_scraper._save_theme_stocks = AsyncMock(return_value=1)
        eastmoney_scraper._refresh_market_snapshots = AsyncMock(return_value=0)

        themes, count = await eastmoney_scraper.run()

        assert len(themes) == 2
        assert count == 4  # 2 themes + 1+1 stocks
        eastmoney_scraper._save_themes.assert_awaited_once()
        assert eastmoney_scraper._save_theme_stocks.await_count == 2

    @pytest.mark.asyncio
    async def test_run_empty_themes_skips_commit(self, eastmoney_scraper):
        eastmoney_scraper.fetch_all_pages = AsyncMock(
            return_value={"data": {"diff": []}}
        )
        eastmoney_scraper._save_themes = AsyncMock()
        eastmoney_scraper.commit_full = AsyncMock()

        themes, count = await eastmoney_scraper.run()

        assert themes == []
        assert count == 0
        eastmoney_scraper.commit_full.assert_not_called()


class TestAKShareCollectCommit:
    @pytest.mark.asyncio
    async def test_collect_full_themes_only_without_saving(self):
        scraper = AKShareScraper()
        frame = pd.DataFrame(
            [
                {
                    "板块代码": "BK0XXX",
                    "板块名称": "锂电池",
                    "涨跌幅": 2.5,
                    "换手率": 1.2,
                    "上涨家数": 30,
                    "下跌家数": 20,
                }
            ]
        )
        scraper._save_themes = AsyncMock(return_value=1)

        with patch("app.scrapers.akshare.ak.stock_board_concept_name_em", return_value=frame):
            draft = await scraper.collect_full()

        assert draft.source == "akshare"
        assert len(draft.themes) == 1
        assert draft.themes[0]["code"] == "BK0XXX"
        assert draft.themes[0]["name"] == "锂电池"
        assert draft.themes[0]["stock_count"] == 50
        assert draft.stocks_by_code == {}
        assert isinstance(draft.trade_date, date)
        scraper._save_themes.assert_not_called()

    @pytest.mark.asyncio
    async def test_commit_full_saves_themes(self):
        scraper = AKShareScraper()
        draft = FullScrapeDraft(
            source="akshare",
            trade_date=date(2026, 7, 27),
            themes=[
                {
                    "name": "锂电池",
                    "code": "BK0XXX",
                    "heat_index": Decimal("1.2"),
                    "rise_fall_pct": Decimal("2.5"),
                    "stock_count": 50,
                    "category": None,
                    "source": "akshare",
                }
            ],
            stocks_by_code={},
        )
        scraper._save_themes = AsyncMock(return_value=1)

        count = await scraper.commit_full(draft)

        assert count == 1
        scraper._save_themes.assert_awaited_once_with(draft.themes)

    @pytest.mark.asyncio
    async def test_collect_full_cancel_before_fetch_raises(self):
        scraper = AKShareScraper()
        cancel = asyncio.Event()
        cancel.set()

        with pytest.raises(asyncio.CancelledError):
            await scraper.collect_full(cancel=cancel)

    @pytest.mark.asyncio
    async def test_run_still_fetches_stocks_not_themes(self):
        """调度器路径保持股票全量采集，不走题材 collect/commit。"""
        scraper = AKShareScraper()
        stocks = [
            {
                "code": "000001",
                "name": "平安银行",
                "current_price": Decimal("10"),
                "rise_fall_pct": Decimal("1"),
                "exchange": "SZ",
            }
        ]
        scraper.fetch_stock_info = AsyncMock(return_value=stocks)
        scraper.save = AsyncMock(return_value=1)
        scraper.collect_full = AsyncMock()

        result_stocks, count = await scraper.run()

        assert result_stocks == stocks
        assert count == 1
        scraper.collect_full.assert_not_called()
        scraper.save.assert_awaited_once_with(stocks)
