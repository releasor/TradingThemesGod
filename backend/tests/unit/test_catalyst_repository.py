"""CatalystRepository 单元测试。"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.catalyst import CatalystClassification
from app.models.theme_driver_event import ThemeDriverEvent
from app.repositories.catalyst import CatalystRepository
from app.services.catalyst_rules import ClassifyResult


def _scalar_result(items):
    result = MagicMock()
    result.all.return_value = items
    return result


def _execute_rows(rows):
    result = MagicMock()
    result.all.return_value = rows
    return result


@pytest.mark.asyncio
async def test_apply_classification_updates_event_and_inserts_audit():
    session = AsyncMock()
    session.add = MagicMock()
    event = ThemeDriverEvent(
        id=1,
        theme_id=10,
        title="证监会发布意见稿",
        summary="监管政策",
        source="新华社",
        url="https://example.com/a",
        url_hash="abc",
        published_at=datetime(2026, 7, 20, tzinfo=UTC),
        relevance_score=80,
        crawled_at=datetime(2026, 7, 20, tzinfo=UTC),
    )
    session.get = AsyncMock(return_value=event)
    repo = CatalystRepository(session)
    result = ClassifyResult(
        freshness="new",
        actor_type="policy",
        confidence=75,
        rationale="命中政策关键词",
    )

    await repo.apply_classification(1, result, method="rules")

    assert event.freshness == "new"
    assert event.actor_type == "policy"
    assert event.classified_by == "rules"
    assert event.classified_at is not None
    session.add.assert_called_once()
    added = session.add.call_args[0][0]
    assert isinstance(added, CatalystClassification)
    assert added.event_id == 1
    assert added.method == "rules"
    assert added.confidence == 75
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_apply_classification_noop_when_event_missing():
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    repo = CatalystRepository(session)

    await repo.apply_classification(
        99,
        ClassifyResult("new", "unknown", 40, "无信号"),
        method="rules",
    )

    session.add.assert_not_called()
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_classify_event_ids_runs_rules_for_each_event():
    session = AsyncMock()
    event = SimpleNamespace(
        id=5,
        theme_id=1,
        title="机器人公司公告中标",
        summary="订单落地",
        source="巨潮",
        event_key="k1",
        published_at=datetime(2026, 7, 20, tzinfo=UTC),
    )
    session.scalars = AsyncMock(
        side_effect=[
            _scalar_result([event]),
            _scalar_result([]),
        ]
    )
    repo = CatalystRepository(session)
    repo.apply_classification = AsyncMock()

    count = await repo.classify_event_ids([5])

    assert count == 1
    repo.apply_classification.assert_awaited_once()
    args = repo.apply_classification.await_args
    assert args.args[0] == 5
    assert args.kwargs["method"] == "rules"
    assert args.args[1].actor_type == "company"


@pytest.mark.asyncio
async def test_classify_recent_loads_unknown_events_only():
    session = AsyncMock()
    unknown_event = SimpleNamespace(
        id=2,
        theme_id=3,
        title="行业动态",
        summary="表现活跃",
        source="新浪",
        event_key=None,
        published_at=datetime(2026, 7, 19, tzinfo=UTC),
    )
    session.scalars = AsyncMock(
        side_effect=[
            _scalar_result([unknown_event]),
            _scalar_result([]),
        ]
    )
    repo = CatalystRepository(session)
    repo._classify_one = AsyncMock()

    count = await repo.classify_recent(days=7)

    assert count == 1
    repo._classify_one.assert_awaited_once_with(unknown_event)
    query = session.scalars.await_args_list[0].args[0]
    compiled = str(query.compile(compile_kwargs={"literal_binds": True}))
    assert "unknown" in compiled


@pytest.mark.asyncio
async def test_resolve_event_ids_builds_keys_from_rows():
    session = AsyncMock()
    session.scalars = AsyncMock(return_value=_scalar_result([11, 12]))
    repo = CatalystRepository(session)
    published_at = datetime(2026, 7, 20, 8, tzinfo=UTC)

    ids = await repo.resolve_event_ids(
        1,
        [{"title": "政策发布", "published_at": published_at}],
    )

    assert ids == [11, 12]
    session.scalars.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_feed_maps_rows():
    session = AsyncMock()
    row = SimpleNamespace(
        event_id=1,
        theme_id=2,
        theme_name="机器人",
        title="标题",
        summary="摘要",
        source="来源",
        url="https://example.com",
        published_at=datetime(2026, 7, 20, tzinfo=UTC),
        relevance_score=70,
        freshness="new",
        actor_type="policy",
        classified_by="rules",
    )
    session.execute = AsyncMock(return_value=_execute_rows([row]))
    repo = CatalystRepository(session)

    items = await repo.list_feed(freshness="new", limit=5)

    assert len(items) == 1
    assert items[0].theme_name == "机器人"
    assert items[0].freshness == "new"


@pytest.mark.asyncio
@patch("app.repositories.catalyst.classify_event")
async def test_classify_one_delegates_to_rules(mock_classify):
    session = AsyncMock()
    event = SimpleNamespace(
        id=7,
        theme_id=1,
        title="标题",
        summary="摘要",
        source="来源",
        event_key=None,
        published_at=datetime(2026, 7, 20, tzinfo=UTC),
    )
    mock_classify.return_value = ClassifyResult("new", "unknown", 40, "无信号")
    repo = CatalystRepository(session)
    repo._load_recent_same_theme = AsyncMock(return_value=[])
    repo.apply_classification = AsyncMock()

    await repo._classify_one(event)

    mock_classify.assert_called_once()
    repo.apply_classification.assert_awaited_once_with(
        7,
        mock_classify.return_value,
        method="rules",
    )
