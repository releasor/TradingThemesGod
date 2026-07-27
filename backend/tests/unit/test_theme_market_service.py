"""题材市场快照服务测试。"""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.theme_market import ThemeMarketService


@pytest.mark.asyncio
async def test_refresh_all_fetches_pools_once_and_writes_each_theme():
    themes = [
        SimpleNamespace(
            id=1,
            rise_fall_pct=Decimal("0.5"),
            stocks=[
                SimpleNamespace(
                    stock=SimpleNamespace(code="1", rise_fall_pct=Decimal("1"))
                )
            ],
        ),
        SimpleNamespace(
            id=2,
            rise_fall_pct=None,
            stocks=[
                SimpleNamespace(
                    stock=SimpleNamespace(code="2", rise_fall_pct=Decimal("-1"))
                )
            ],
        ),
    ]
    session = AsyncMock()
    theme_repo = AsyncMock()
    theme_repo.list_with_stock_quotes.return_value = themes
    insight_repo = AsyncMock()
    limit_pool = AsyncMock()
    limit_pool.fetch.return_value = ({"000001"}, {"000002"})
    service = ThemeMarketService(session, theme_repo, insight_repo, limit_pool)

    count = await service.refresh_all(date(2026, 7, 20))

    assert count == 2
    limit_pool.fetch.assert_awaited_once_with(date(2026, 7, 20))
    assert insight_repo.upsert_snapshot.await_count == 2
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_refresh_for_theme_codes_skips_live_quote_on_historical_days():
    """历史日补快照时不应写入当前题材涨跌幅，避免污染周期指数强度。"""
    themes = [
        SimpleNamespace(
            id=1,
            rise_fall_pct=Decimal("-2.04"),
            stocks=[
                SimpleNamespace(
                    stock=SimpleNamespace(code="1", rise_fall_pct=Decimal("1"))
                )
            ],
        ),
    ]
    session = AsyncMock()
    theme_repo = AsyncMock()
    theme_repo.list_with_stock_quotes_by_codes.return_value = themes
    insight_repo = AsyncMock()
    limit_pool = AsyncMock()
    limit_pool.fetch.return_value = (set(), set())
    service = ThemeMarketService(session, theme_repo, insight_repo, limit_pool)

    await service.refresh_for_theme_codes({"BK0500"}, date(2026, 7, 10))

    kwargs = insight_repo.upsert_snapshot.await_args.kwargs
    assert kwargs["rise_fall_pct"] is None


@pytest.mark.asyncio
async def test_refresh_for_theme_codes_keeps_live_quote_on_today(monkeypatch):
    monkeypatch.setattr(
        "app.services.theme_market.date",
        SimpleNamespace(today=lambda: date(2026, 7, 24)),
    )
    themes = [
        SimpleNamespace(
            id=1,
            rise_fall_pct=Decimal("-2.04"),
            stocks=[
                SimpleNamespace(
                    stock=SimpleNamespace(code="1", rise_fall_pct=Decimal("1"))
                )
            ],
        ),
    ]
    session = AsyncMock()
    theme_repo = AsyncMock()
    theme_repo.list_with_stock_quotes_by_codes.return_value = themes
    insight_repo = AsyncMock()
    limit_pool = AsyncMock()
    limit_pool.fetch.return_value = (set(), set())
    service = ThemeMarketService(session, theme_repo, insight_repo, limit_pool)

    await service.refresh_for_theme_codes({"BK0500"}, date(2026, 7, 24))

    kwargs = insight_repo.upsert_snapshot.await_args.kwargs
    assert kwargs["rise_fall_pct"] == Decimal("-2.04")
