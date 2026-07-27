"""AkShare 短线默认拉取测试（mock akshare，不打外网）。"""

import json
from datetime import date
from unittest.mock import patch

import pandas as pd
import pytest

from app.scrapers.akshare_short_term import (
    _json_safe,
    fetch_dragon_tiger_entries,
    fetch_limit_pools,
)
from app.scrapers.dragon_tiger import DragonTigerScraper
from app.scrapers.short_term_signals import ShortTermSignalScraper


def test_json_safe_handles_date_and_nan():
    payload = _json_safe({"d": date(2026, 7, 24), "n": float("nan"), "ok": 1})
    assert payload["d"] == "2026-07-24"
    assert payload["n"] is None
    json.dumps(payload)


@pytest.mark.asyncio
async def test_fetch_limit_pools_maps_frames():
    limit_up = pd.DataFrame(
        [{"代码": "000001", "名称": "平安银行", "连板数": 1, "是否一字板": "否"}]
    )
    failed = pd.DataFrame([{"代码": "000002", "名称": "万科A"}])
    near = pd.DataFrame([{"代码": "000003", "名称": "国农科技"}])

    with (
        patch("app.scrapers.akshare_short_term.ak.stock_zt_pool_em", return_value=limit_up),
        patch("app.scrapers.akshare_short_term.ak.stock_zt_pool_zbgc_em", return_value=failed),
        patch("app.scrapers.akshare_short_term.ak.stock_zt_pool_strong_em", return_value=near),
    ):
        pools = await fetch_limit_pools(date(2026, 7, 24))

    assert pools["limit_up"][0]["代码"] == "000001"
    assert pools["failed_limit_up"][0]["代码"] == "000002"
    assert pools["near_limit_up"][0]["代码"] == "000003"


@pytest.mark.asyncio
async def test_default_signal_scraper_uses_injected_akshare_shaped_data():
    async def fake_fetch(_trade_date):
        return {"limit_up": [{"code": "000001", "连板数": 1}]}

    result = await ShortTermSignalScraper(fetch_pools=fake_fetch).fetch(date(2026, 7, 24))
    assert result.success is True
    assert result.items[0]["stock_code"] == "000001"


@pytest.mark.asyncio
async def test_fetch_and_parse_dragon_tiger():
    frame = pd.DataFrame(
        [
            {
                "代码": "600000",
                "名称": "浦发银行",
                "上榜原因": "涨幅偏离值达7%",
                "买入额": 1e8,
                "卖出额": 2e7,
            }
        ]
    )
    with patch(
        "app.scrapers.akshare_short_term.ak.stock_lhb_detail_em", return_value=frame
    ):
        rows = await fetch_dragon_tiger_entries(date(2026, 7, 24))

    async def fixed(_d):
        return rows

    parsed = await DragonTigerScraper(fetch_entries=fixed).fetch(date(2026, 7, 24))
    assert parsed.success is True
    assert parsed.items[0]["stock_code"] == "600000"
    assert float(parsed.items[0]["net_amount"]) == pytest.approx(8e7)
