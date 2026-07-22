"""题材洞察仓储测试。"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.theme_insights import build_event_key
from app.repositories.theme_insight import ThemeInsightRepository, canonicalize_url


def _result(items):
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


@pytest.mark.asyncio
async def test_recent_events_falls_back_to_thirty_days_when_seven_days_is_short():
    now = datetime(2026, 7, 20, tzinfo=UTC)
    recent = [SimpleNamespace(title="近一天")]
    expanded = [
        SimpleNamespace(title="近一天"),
        SimpleNamespace(title="近十天"),
    ]
    session = AsyncMock()
    session.execute.side_effect = [_result(recent), _result(expanded)]
    repository = ThemeInsightRepository(session)

    items = await repository.list_recent_events(1, now=now, limit=5)

    assert items == expanded
    assert session.execute.await_count == 2
    first_sql = str(
        session.execute.await_args_list[0]
        .args[0]
        .compile(compile_kwargs={"literal_binds": True})
    )
    second_sql = str(
        session.execute.await_args_list[1]
        .args[0]
        .compile(compile_kwargs={"literal_binds": True})
    )
    assert str((now - timedelta(days=7)).date()) in first_sql
    assert str((now - timedelta(days=30)).date()) in second_sql


@pytest.mark.asyncio
async def test_recent_events_does_not_expand_when_limit_is_met():
    now = datetime(2026, 7, 20, tzinfo=UTC)
    recent = [SimpleNamespace(title=str(index)) for index in range(5)]
    session = AsyncMock()
    session.execute.return_value = _result(recent)
    repository = ThemeInsightRepository(session)

    items = await repository.list_recent_events(1, now=now, limit=5)

    assert items == recent
    session.execute.assert_awaited_once()


def test_canonicalize_url_removes_tracking_fragment_and_default_port():
    assert (
        canonicalize_url("HTTPS://Example.COM:443/path?utm_source=test&b=2&a=1#section")
        == "https://example.com/path?a=1&b=2"
    )


@pytest.mark.asyncio
async def test_event_upsert_uses_canonical_url_and_refreshes_updated_at():
    session = AsyncMock()
    scalars_result = MagicMock()
    scalars_result.all.return_value = []
    session.scalars = AsyncMock(return_value=scalars_result)
    repository = ThemeInsightRepository(session)

    await repository.upsert_events(
        1,
        [
            {
                "title": "政策发布",
                "summary": "摘要",
                "source": "示例网",
                "url": "https://EXAMPLE.com:443/a?utm_source=x#fragment",
                "published_at": datetime(2026, 7, 20, tzinfo=UTC),
                "relevance_score": 80,
                "crawled_at": datetime(2026, 7, 20, tzinfo=UTC),
            }
        ],
    )

    statement = session.execute.await_args.args[0]
    assert "https://example.com/a" in statement.compile().params.values()
    compiled = str(statement.compile()).lower()
    assert "event_key" in compiled
    assert "url = values(url)" in compiled
    assert "updated_at" in compiled


@pytest.mark.asyncio
async def test_event_upsert_counts_same_event_on_later_refresh_as_update():
    session = AsyncMock()
    first_result = MagicMock()
    first_result.all.return_value = []
    second_result = MagicMock()
    session.scalars = AsyncMock(side_effect=[first_result, second_result])
    repository = ThemeInsightRepository(session)
    published_at = datetime(2026, 7, 20, tzinfo=UTC)
    event = {
        "title": "政策发布",
        "summary": "摘要",
        "source": "示例网",
        "url": "https://example.com/a",
        "published_at": published_at,
        "relevance_score": 80,
        "crawled_at": published_at,
    }
    second_result.all.return_value = [build_event_key(event["title"], published_at)]

    first = await repository.upsert_events(1, [event])
    second = await repository.upsert_events(
        1, [{**event, "url": "https://other.com/b"}]
    )

    assert first == (1, 0)
    assert second == (0, 1)
