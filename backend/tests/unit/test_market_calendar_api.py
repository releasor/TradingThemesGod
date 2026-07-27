"""市场交易日历 API 测试。"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.main import app
from app.schemas.trading_calendar import TradingCalendarStatus
from app.services.trading_calendar import TradingCalendar


def _auth_user():
    return SimpleNamespace(id=1, username="tester")


def test_calendar_status_returns_200():
    status = TradingCalendarStatus(
        source="akshare_sina",
        last_synced_at=None,
        row_count=2,
        min_date=date(2026, 7, 23),
        max_date=date(2026, 7, 24),
        last_error=None,
        degraded=False,
        today_is_trade_day=False,
        data_trade_date=date(2026, 7, 24),
        missing_sources=[],
    )
    TradingCalendar.clear()
    with patch("app.api.market_calendar.TradingCalendarSyncService") as svc_cls:
        svc = svc_cls.return_value
        svc.ensure_memory_loaded = AsyncMock()
        svc.build_status = AsyncMock(return_value=status)
        response = TestClient(app).get("/api/v1/market/calendar/status")
    assert response.status_code == 200
    assert response.json()["data_trade_date"] == "2026-07-24"


def test_calendar_resolve_returns_trade_date():
    TradingCalendar.load_dates({date(2026, 9, 30), date(2026, 10, 8)})
    with patch("app.api.market_calendar.TradingCalendarSyncService") as svc_cls:
        svc = svc_cls.return_value
        svc.ensure_memory_loaded = AsyncMock()
        response = TestClient(app).get(
            "/api/v1/market/calendar/resolve", params={"date": "2026-10-05"}
        )
    TradingCalendar.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["input_date"] == "2026-10-05"
    assert body["trade_date"] == "2026-09-30"


def test_calendar_sync_requires_auth_and_returns_status(monkeypatch):
    app.dependency_overrides[get_current_user] = _auth_user
    TradingCalendar.clear()

    monkeypatch.setattr(
        "app.api.market_calendar.fetch_akshare_trade_dates",
        lambda: [date(2026, 7, 22), date(2026, 7, 23), date(2026, 7, 24)],
    )

    try:
        with patch("app.api.market_calendar.TradingCalendarSyncService") as svc_cls:
            svc = svc_cls.return_value
            svc.repo = AsyncMock()
            svc.repo.replace_all = AsyncMock(return_value=3)
            svc.repo.upsert_meta = AsyncMock()
            response = TestClient(app).post("/api/v1/market/calendar/sync")
        assert response.status_code == 200
        assert response.json()["row_count"] == 3
        assert response.json()["degraded"] is False
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        TradingCalendar.clear()
