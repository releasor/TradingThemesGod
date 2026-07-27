"""ReviewRepository 单元测试（mock session）。"""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.review import ReviewRun
from app.repositories.review import ReviewRepository


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.scalar = AsyncMock(return_value=None)
    session.scalars = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_create_run_adds_running_run(mock_session):
    repo = ReviewRepository(mock_session)
    trade_date = date(2026, 7, 24)

    run = await repo.create_run(
        trade_date=trade_date,
        run_type="overview_analyze",
        request_meta={"source": "test"},
    )

    mock_session.add.assert_called_once()
    added = mock_session.add.call_args[0][0]
    assert isinstance(added, ReviewRun)
    assert added.trade_date == trade_date
    assert added.run_type == "overview_analyze"
    assert added.status == "running"
    assert added.request_meta == {"source": "test"}
    assert added.started_at.tzinfo is not None
    mock_session.flush.assert_awaited_once()
    assert run.status == "running"


@pytest.mark.asyncio
async def test_finish_run_updates_status_and_source_status(mock_session):
    run = ReviewRun(
        id=1,
        trade_date=date(2026, 7, 24),
        run_type="signals_refresh",
        status="running",
        source_status={"signals": {"count": 1}},
        request_meta={},
        started_at=datetime(2026, 7, 24, 8, 0, tzinfo=timezone.utc),
        finished_at=None,
    )
    mock_session.scalar = AsyncMock(return_value=run)
    repo = ReviewRepository(mock_session)

    await repo.finish_run(
        1,
        status="failed",
        source_status={"signals": {"count": 2}},
        error="boom",
    )

    assert run.status == "failed"
    assert run.finished_at is not None
    assert run.finished_at.tzinfo is not None
    assert run.source_status["signals"]["count"] == 2
    assert run.source_status["error"] == "boom"
    mock_session.flush.assert_awaited_once()
