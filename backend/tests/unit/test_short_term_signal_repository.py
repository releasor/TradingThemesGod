"""ShortTermSignalRepository 单元测试（mock session）。"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.short_term_signal import DailyStockSignal, ShortTermSignalRun
from app.repositories.short_term_signal import ShortTermSignalRepository


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.scalar = AsyncMock(return_value=None)
    session.scalars = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_create_and_finish_run(mock_session):
    repo = ShortTermSignalRepository(mock_session)
    run = await repo.create_run(date(2026, 7, 25))
    mock_session.add.assert_called()
    mock_session.flush.assert_awaited()
    assert run.trade_date == date(2026, 7, 25)
    assert run.status == "running"

    finished = await repo.finish_run(
        run, status="partial", source_status={"dragon_tiger": {"success": False}}
    )
    assert finished.status == "partial"
    assert finished.finished_at is not None


@pytest.mark.asyncio
async def test_upsert_signal_inserts_when_missing(mock_session):
    repo = ShortTermSignalRepository(mock_session)
    mock_session.scalar = AsyncMock(return_value=None)
    row = await repo.upsert_signal(
        {
            "trade_date": date(2026, 7, 25),
            "stock_id": 1,
            "signal_type": "limit_up",
            "streak_days": 1,
            "source": "test",
        }
    )
    mock_session.add.assert_called()
    assert row.signal_type == "limit_up"
    assert row.streak_days == 1


@pytest.mark.asyncio
async def test_upsert_signal_updates_existing(mock_session):
    existing = DailyStockSignal(
        trade_date=date(2026, 7, 25),
        stock_id=1,
        signal_type="limit_up",
        streak_days=1,
        source="old",
    )
    mock_session.scalar = AsyncMock(return_value=existing)
    repo = ShortTermSignalRepository(mock_session)
    row = await repo.upsert_signal(
        {
            "trade_date": date(2026, 7, 25),
            "stock_id": 1,
            "signal_type": "limit_up",
            "streak_days": 2,
            "source": "new",
        }
    )
    assert row is existing
    assert row.streak_days == 2
    assert row.source == "new"
    # update path should not add a new instance
    mock_session.add.assert_not_called()
