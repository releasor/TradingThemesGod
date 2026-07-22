"""AKShare 涨跌停池适配测试。"""

from datetime import date

import pandas as pd
import pytest

from app.integrations.market.limit_pool import LimitPoolProvider


@pytest.mark.asyncio
async def test_limit_pool_normalizes_codes_and_calls_expected_date():
    calls: list[str] = []

    def fetch(date: str):
        calls.append(date)
        return pd.DataFrame({"代码": [1, "600001"]})

    provider = LimitPoolProvider(fetch, fetch)

    limit_up, limit_down = await provider.fetch(date(2026, 7, 20))

    assert calls == ["20260720", "20260720"]
    assert limit_up == {"000001", "600001"}
    assert limit_down == {"000001", "600001"}


@pytest.mark.asyncio
async def test_limit_pool_failure_is_reported_as_unavailable():
    def fail(date: str):
        raise RuntimeError(date)

    provider = LimitPoolProvider(fail, fail)

    assert await provider.fetch(date(2026, 7, 20)) == (None, None)
