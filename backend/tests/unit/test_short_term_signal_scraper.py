"""短线信号与龙虎榜解析测试。"""

from datetime import date

import pytest

from app.scrapers.dragon_tiger import DragonTigerScraper, parse_dragon_tiger_rows
from app.scrapers.short_term_signals import (
    ShortTermSignalScraper,
    parse_limit_pools,
)


def test_parse_limit_pools_maps_signal_types():
    items = parse_limit_pools(
        {
            "limit_up": [
                {
                    "代码": "000001",
                    "名称": "平安银行",
                    "连板数": 1,
                    "首次封板时间": "09:35:00",
                    "最新价": 12.3,
                }
            ],
            "failed_limit_up": [{"code": "000002", "name": "万科A", "is_failed": True}],
            "one_word_limit_up": [{"code": "300001", "一字板": True, "连板数": 2}],
        },
        trade_date=date(2026, 7, 25),
    )
    by_type = {item["signal_type"]: item for item in items}
    assert by_type["limit_up"]["stock_code"] == "000001"
    assert by_type["limit_up"]["streak_days"] == 1
    assert by_type["failed_limit_up"]["is_failed"] is True
    assert by_type["one_word_limit_up"]["is_one_word"] is True
    assert by_type["one_word_limit_up"]["streak_days"] == 2


def test_parse_dragon_tiger_computes_net():
    items = parse_dragon_tiger_rows(
        [
            {
                "股票代码": "600000",
                "上榜原因": "日涨幅偏离值达到7%",
                "买入额": 1.5e8,
                "卖出额": 0.5e8,
            }
        ],
        trade_date=date(2026, 7, 25),
    )
    assert len(items) == 1
    assert items[0]["stock_code"] == "600000"
    assert float(items[0]["net_amount"]) == pytest.approx(1.0e8)


@pytest.mark.asyncio
async def test_signal_scraper_uses_injected_fetch():
    async def fetch(_trade_date):
        return {"limit_up": [{"code": "000001", "连板数": 1}]}

    result = await ShortTermSignalScraper(fetch_pools=fetch).fetch(date(2026, 7, 25))
    assert result.success is True
    assert result.items[0]["signal_type"] == "limit_up"


@pytest.mark.asyncio
async def test_dragon_tiger_scraper_failure():
    async def fetch(_trade_date):
        raise RuntimeError("源不可用")

    result = await DragonTigerScraper(fetch_entries=fetch).fetch(date(2026, 7, 25))
    assert result.success is False
    assert "源不可用" in (result.error or "")
