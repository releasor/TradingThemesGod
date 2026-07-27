"""CatalystService 单元测试。"""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models.theme_driver_event import ThemeDriverEvent
from app.repositories.catalyst import FeedRow
from app.schemas.catalyst import CatalystEnsureResponse
from app.services.catalyst import CatalystService


def _feed_row() -> FeedRow:
    return FeedRow(
        event_id=1,
        theme_id=2,
        theme_name="机器人",
        title="政策加码",
        summary="摘要",
        source="新华社",
        url="https://example.com/a",
        published_at=datetime(2026, 7, 20, tzinfo=UTC),
        relevance_score=80,
        freshness="new",
        actor_type="policy",
        classified_by="rules",
    )


@pytest.mark.asyncio
async def test_get_feed_maps_items():
    session = AsyncMock()
    service = CatalystService(session)
    service.repo = AsyncMock()
    service.repo.list_feed.return_value = [_feed_row()]
    service.repo.count_feed.return_value = 1

    result = await service.get_feed(freshness="new", limit=10)

    assert len(result.items) == 1
    item = result.items[0]
    assert item.event_id == 1
    assert item.theme_name == "机器人"
    assert item.freshness == "new"
    assert item.actor_type == "policy"
    assert result.total == 1
    service.repo.list_feed.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_theme_summary_empty_news():
    session = AsyncMock()
    theme = SimpleNamespace(id=5, name="低空经济", deleted_at=None)
    session.get = AsyncMock(return_value=theme)
    session.scalar = AsyncMock(return_value=None)

    service = CatalystService(session)
    service.repo = AsyncMock()
    service.repo.count_by_theme.return_value = {"new": 2, "policy": 1}
    service.repo.list_theme_events.return_value = []
    service.repo.list_news_headlines_for_theme.return_value = []

    result = await service.get_theme_summary(5)

    assert result.theme_id == 5
    assert result.theme_name == "低空经济"
    assert result.lifecycle_stage is None
    assert result.strength_score is None
    assert result.counts == {"new": 2, "policy": 1}
    assert result.recent_events == []
    assert result.news_headlines == []
    service.repo.list_news_headlines_for_theme.assert_awaited_once_with("低空经济", limit=8)


@pytest.mark.asyncio
async def test_get_theme_summary_not_found():
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    service = CatalystService(session)

    with pytest.raises(HTTPException) as exc_info:
        await service.get_theme_summary(999)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_ensure_classify_returns_rules_count():
    session = AsyncMock()
    service = CatalystService(session)
    service.repo = AsyncMock()
    service.repo.classify_recent.return_value = 3

    with patch("app.services.catalyst.asyncio.create_task") as create_task:
        result = await service.ensure_classify(days=7, use_model=False)

    assert isinstance(result, CatalystEnsureResponse)
    assert result.classified_rules == 3
    assert result.model_queued is False
    create_task.assert_not_called()
    service.repo.classify_recent.assert_awaited_once_with(days=7)
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_ensure_classify_with_user_queues_background_task():
    session = AsyncMock()
    service = CatalystService(session)
    service.repo = AsyncMock()
    service.repo.classify_recent.return_value = 2

    mock_task = MagicMock()
    with patch(
        "app.services.catalyst.asyncio.create_task", return_value=mock_task
    ) as create_task:
        result = await service.ensure_classify(days=7, use_model=True, user_id=42)

    assert result.classified_rules == 2
    assert result.model_queued is True
    create_task.assert_called_once()
    coro = create_task.call_args.args[0]
    assert hasattr(coro, "cr_code") or hasattr(coro, "send")
    coro.close()
    session.commit.assert_awaited_once()
