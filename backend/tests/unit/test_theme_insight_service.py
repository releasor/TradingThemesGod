"""题材互联网研究刷新服务测试。"""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.services.theme_insight import ThemeInsightRefreshService
from app.services.web_research import ResearchSource


@pytest.mark.asyncio
async def test_refresh_persists_valid_profile_and_relevant_events():
    session = AsyncMock()
    research = MagicMock()
    published_at = datetime(2026, 7, 19, 8, tzinfo=UTC)
    source = ResearchSource(
        "来源",
        "https://example.com/a",
        "机器人产业政策与应用场景正文",
        "示例网",
        published_at,
    )
    research.research_profile = AsyncMock(return_value=[source])
    research.research_driver_events = AsyncMock(return_value=[source])
    news = MagicMock()
    news.list_theme_candidates = AsyncMock(return_value=[])
    providers = MagicMock()
    providers.get_default = AsyncMock(return_value=SimpleNamespace())
    adapter = MagicMock()
    adapter.complete = AsyncMock(
        return_value='{"profile":{"definition":"定义","core_logic":"逻辑","applications":["制造"],"catalysts":["政策"],"risks":["竞争"],"source_urls":["https://example.com/a"]},"events":[{"title":"政策发布","summary":"支持机器人应用","source_url":"https://example.com/a","published_at":"2026-07-20T08:00:00+08:00","relevance_score":88}]}'
    )
    providers.adapter.return_value = adapter
    insights = MagicMock()
    insights.upsert_profile = AsyncMock()
    insights.upsert_events = AsyncMock(return_value=(1, 0))
    service = ThemeInsightRefreshService(session, research, providers, news, insights)
    service._theme_context = AsyncMock(
        return_value=(
            SimpleNamespace(id=1, name="机器人", description=None, tags=[]),
            [],
        )
    )

    result = await service.refresh(1)

    assert result.profile_updated is True
    assert result.inserted_events == 1
    assert result.degraded is False
    insights.upsert_profile.assert_awaited_once()
    assert insights.upsert_profile.await_args.args[2][0]["published_at"] == published_at
    insights.upsert_events.assert_awaited_once()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_ai_failure_uses_keyword_event_fallback_without_overwriting_profile():
    session = AsyncMock()
    source = ResearchSource(
        "机器人产业政策发布",
        "https://example.com/policy",
        "政策支持机器人示范应用",
        "示例网",
    )
    research = MagicMock()
    research.research_profile = AsyncMock(return_value=[source])
    research.research_driver_events = AsyncMock(return_value=[source])
    research.failed_sources = {"DuckDuckGo"}
    news = MagicMock()
    news.list_theme_candidates = AsyncMock(return_value=[])
    providers = MagicMock()
    providers.get_default = AsyncMock(side_effect=HTTPException(409, "模型不可用"))
    insights = MagicMock()
    insights.upsert_profile = AsyncMock()
    insights.upsert_events = AsyncMock(return_value=(1, 0))
    service = ThemeInsightRefreshService(session, research, providers, news, insights)
    service._theme_context = AsyncMock(
        return_value=(
            SimpleNamespace(id=1, name="机器人", description=None, tags=[]),
            [],
        )
    )

    result = await service.refresh(1)

    assert result.degraded is True
    assert result.inserted_events == 1
    assert result.failed_sources == ["DuckDuckGo"]
    insights.upsert_profile.assert_not_awaited()


@pytest.mark.asyncio
async def test_refresh_skips_profile_research_when_profile_is_fresh():
    session = AsyncMock()
    source = ResearchSource(
        "机器人订单发布",
        "https://example.com/order",
        "机器人企业发布新订单",
        "示例网",
    )
    research = MagicMock()
    research.research_profile = AsyncMock(return_value=[source])
    research.research_driver_events = AsyncMock(return_value=[source])
    news = MagicMock()
    news.list_theme_candidates = AsyncMock(return_value=[])
    providers = MagicMock()
    providers.get_default = AsyncMock(side_effect=HTTPException(409, "模型不可用"))
    insights = MagicMock()
    insights.upsert_profile = AsyncMock()
    insights.upsert_events = AsyncMock(return_value=(1, 0))
    service = ThemeInsightRefreshService(session, research, providers, news, insights)
    service._theme_context = AsyncMock(
        return_value=(SimpleNamespace(id=1, name="机器人", description=None), [])
    )

    result = await service.refresh(1, refresh_profile=False)

    research.research_profile.assert_not_awaited()
    insights.upsert_profile.assert_not_awaited()
    assert result.profile_updated is False
