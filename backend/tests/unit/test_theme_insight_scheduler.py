"""题材研究周期调度测试。"""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import Settings
from app.services.theme_insight_scheduler import ThemeInsightScheduler


def test_theme_insight_periodic_refresh_is_enabled_by_default():
    settings = Settings(_env_file=None)

    assert settings.THEME_INSIGHT_AUTO_ENABLED is True
    assert settings.THEME_INSIGHT_INTERVAL_SECONDS == 3600
    assert settings.THEME_INSIGHT_BATCH_SIZE == 10
    assert settings.THEME_PROFILE_MAX_AGE_DAYS == 7


@pytest.mark.asyncio
async def test_scheduler_start_is_idempotent_and_stop_cancels_task():
    scheduler = ThemeInsightScheduler()
    scheduler.run_batch = AsyncMock()

    first = scheduler.start(interval_seconds=3600)
    second = scheduler.start(interval_seconds=3600)
    assert first is second

    await scheduler.stop()
    assert scheduler._task is None


@pytest.mark.asyncio
async def test_scheduler_loop_recovers_after_batch_failure():
    scheduler = ThemeInsightScheduler()
    scheduler.run_batch = AsyncMock(
        side_effect=[RuntimeError("database unavailable"), asyncio.CancelledError()]
    )

    with (
        patch(
            "app.services.theme_insight_scheduler.asyncio.sleep",
            new_callable=AsyncMock,
        ),
        pytest.raises(asyncio.CancelledError),
    ):
        await scheduler._loop(interval_seconds=1)

    assert scheduler.run_batch.await_count == 2


@pytest.mark.asyncio
async def test_scheduler_prioritizes_old_event_refresh_and_skips_fresh_profile():
    now = datetime.now(UTC)
    rows = [
        (1, now - timedelta(days=1), now - timedelta(hours=4), None),
        (2, now - timedelta(days=8), now - timedelta(hours=2), None),
    ]
    result = MagicMock()
    result.all.return_value = rows
    session = AsyncMock()
    session.execute.return_value = result
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=session)
    context.__aexit__ = AsyncMock(return_value=False)
    service = MagicMock()
    service.refresh = AsyncMock()
    service.insights.mark_refresh_attempt = AsyncMock()
    service.research.middleware.close = AsyncMock()
    scheduler = ThemeInsightScheduler(batch_size=2)

    with (
        patch(
            "app.services.theme_insight_scheduler.AsyncSessionLocal",
            return_value=context,
        ),
        patch(
            "app.services.theme_insight_scheduler.ThemeInsightRefreshService",
            return_value=service,
        ),
    ):
        completed = await scheduler.run_batch()

    assert completed == 2
    assert service.refresh.await_args_list[0].args == (1,)
    assert service.refresh.await_args_list[0].kwargs == {"refresh_profile": False}
    assert service.refresh.await_args_list[1].args == (2,)
    assert service.refresh.await_args_list[1].kwargs == {"refresh_profile": True}
    assert service.insights.mark_refresh_attempt.await_count == 2


@pytest.mark.asyncio
async def test_scheduler_uses_persisted_cursor_after_restart():
    now = datetime.now(UTC)
    rows = [
        (1, None, None, now),
        (2, None, None, None),
    ]
    result = MagicMock()
    result.all.return_value = rows
    session = AsyncMock()
    session.execute.return_value = result
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=session)
    context.__aexit__ = AsyncMock(return_value=False)
    service = MagicMock()
    service.refresh = AsyncMock()
    service.insights.mark_refresh_attempt = AsyncMock()
    service.research.middleware.close = AsyncMock()

    with (
        patch(
            "app.services.theme_insight_scheduler.AsyncSessionLocal",
            return_value=context,
        ),
        patch(
            "app.services.theme_insight_scheduler.ThemeInsightRefreshService",
            return_value=service,
        ),
    ):
        await ThemeInsightScheduler(batch_size=1).run_batch()

    service.refresh.assert_awaited_once_with(2, refresh_profile=True)
