"""TradingCalendarSyncService 单元测试。"""

from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.trading_calendar import TradingCalendar


@pytest.fixture(autouse=True)
def _clear_calendar():
    TradingCalendar.clear()
    yield
    TradingCalendar.clear()


@pytest.mark.asyncio
async def test_sync_replaces_days_and_refreshes_memory(monkeypatch):
    session = AsyncMock()
    repo = AsyncMock()
    repo.replace_all = AsyncMock(return_value=3)
    repo.list_all_dates = AsyncMock(
        return_value=[date(2026, 7, 22), date(2026, 7, 23), date(2026, 7, 24)]
    )
    repo.get_meta = AsyncMock(return_value=None)
    repo.upsert_meta = AsyncMock(
        return_value=SimpleNamespace(
            source="akshare_sina",
            last_synced_at=datetime(2026, 7, 24, tzinfo=timezone.utc),
            row_count=3,
            min_date=date(2026, 7, 22),
            max_date=date(2026, 7, 24),
            last_error=None,
        )
    )

    monkeypatch.setattr(
        "app.services.trading_calendar_sync.fetch_akshare_trade_dates",
        lambda: [date(2026, 7, 22), date(2026, 7, 23), date(2026, 7, 24)],
    )

    from app.services.trading_calendar_sync import TradingCalendarSyncService

    svc = TradingCalendarSyncService(session)
    svc.repo = repo
    status = await svc.sync(force=True)
    assert status.row_count == 3
    assert TradingCalendar.is_trade_day(date(2026, 7, 24))
    assert TradingCalendar.degraded is False
    repo.replace_all.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_failure_records_error_keeps_memory(monkeypatch):
    session = AsyncMock()
    repo = AsyncMock()
    repo.list_all_dates = AsyncMock(return_value=[date(2026, 7, 24)])
    repo.get_meta = AsyncMock(return_value=None)
    repo.upsert_meta = AsyncMock(
        return_value=SimpleNamespace(
            source="akshare_sina",
            last_synced_at=None,
            row_count=1,
            min_date=date(2026, 7, 24),
            max_date=date(2026, 7, 24),
            last_error="boom",
        )
    )

    def boom():
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "app.services.trading_calendar_sync.fetch_akshare_trade_dates",
        boom,
    )

    TradingCalendar.load_dates({date(2026, 7, 24)})

    from app.services.trading_calendar_sync import TradingCalendarSyncService

    svc = TradingCalendarSyncService(session)
    svc.repo = repo
    status = await svc.sync(force=True)
    assert status.last_error == "boom"
    assert TradingCalendar.is_trade_day(date(2026, 7, 24))
    repo.replace_all.assert_not_called()
