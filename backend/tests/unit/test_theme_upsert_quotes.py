"""题材行情按 code 回写多源单元测试。"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.scrapers.theme_upsert import apply_theme_quotes, batch_quotes_are_all_zero


def test_batch_quotes_are_all_zero():
    assert batch_quotes_are_all_zero([]) is True
    assert batch_quotes_are_all_zero([{"rise_fall_pct": 0}, {"rise_fall_pct": "0.0"}]) is True
    assert batch_quotes_are_all_zero([{"rise_fall_pct": 0}, {"rise_fall_pct": 1.2}]) is False


@pytest.mark.asyncio
async def test_apply_theme_quotes_updates_all_sources_for_same_code():
    east = MagicMock()
    east.code = "BK0815"
    east.name = "昨日涨停"
    east.rise_fall_pct = Decimal("0")
    east.heat_index = Decimal("0")
    east.stock_count = 0

    ak = MagicMock()
    ak.code = "BK0815"
    ak.name = "昨日涨停"
    ak.rise_fall_pct = Decimal("0")
    ak.heat_index = Decimal("0")
    ak.stock_count = 0

    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [east, ak]
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()

    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)

    with patch("app.scrapers.theme_upsert.AsyncSessionLocal", return_value=session_cm):
        updated = await apply_theme_quotes(
            [
                {
                    "code": "BK0815",
                    "name": "昨日涨停",
                    "rise_fall_pct": Decimal("2.5"),
                    "heat_index": Decimal("1.1"),
                    "stock_count": 12,
                    "source": "eastmoney",
                }
            ]
        )

    assert updated == 2
    assert east.rise_fall_pct == Decimal("2.5")
    assert ak.rise_fall_pct == Decimal("2.5")
    assert east.stock_count == 12
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_apply_theme_quotes_preserves_nonzero_when_batch_all_zero():
    theme = MagicMock()
    theme.code = "BK0815"
    theme.name = "昨日涨停"
    theme.rise_fall_pct = Decimal("3.2")
    theme.heat_index = Decimal("1")
    theme.stock_count = 8

    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [theme]
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()

    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)

    with patch("app.scrapers.theme_upsert.AsyncSessionLocal", return_value=session_cm):
        await apply_theme_quotes(
            [{"code": "BK0815", "name": "昨日涨停", "rise_fall_pct": Decimal("0")}]
        )

    assert theme.rise_fall_pct == Decimal("3.2")
