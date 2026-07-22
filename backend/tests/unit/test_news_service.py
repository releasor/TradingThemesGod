"""新闻聚合服务测试。"""

from datetime import datetime
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest

from app.services.news import NewsService, calculate_heat_scores


@pytest.mark.asyncio
async def test_refresh_continues_when_one_source_fails():
    good_source = AsyncMock()
    good_source.name = "good"
    good_source.fetch.return_value = [
        {"title": "有效新闻", "url": "https://example.com/news/1"}
    ]
    bad_source = AsyncMock()
    bad_source.name = "bad"
    bad_source.fetch.side_effect = RuntimeError("来源不可用")
    repository = AsyncMock()
    repository.upsert_many.return_value = 1
    service = NewsService(repository, sources=[good_source, bad_source])

    result = await service.refresh()

    assert result.success is True
    assert result.fetched_count == 1
    assert result.inserted_count == 1
    assert result.sources[0].success is True
    assert result.sources[1].success is False
    assert result.sources[1].error == "来源不可用"


@pytest.mark.asyncio
async def test_refresh_fails_when_every_source_fails():
    source = AsyncMock()
    source.name = "broken"
    source.fetch.side_effect = RuntimeError("连接失败")
    service = NewsService(AsyncMock(), sources=[source])

    result = await service.refresh()

    assert result.success is False
    assert result.inserted_count == 0


@pytest.mark.asyncio
async def test_refresh_reports_empty_source_as_failed():
    source = AsyncMock()
    source.name = "empty"
    source.fetch.return_value = []
    service = NewsService(AsyncMock(), sources=[source])

    result = await service.refresh()

    assert result.success is False
    assert result.sources[0].success is False
    assert "未抓取到有效新闻" in result.sources[0].error


@pytest.mark.asyncio
async def test_refresh_only_fetches_enabled_sources():
    enabled_source = AsyncMock()
    enabled_source.name = "enabled"
    enabled_source.fetch.return_value = [
        {"title": "启用渠道新闻", "url": "https://example.com/enabled"}
    ]
    disabled_source = AsyncMock()
    disabled_source.name = "disabled"
    repository = AsyncMock()
    repository.upsert_many.return_value = 1
    service = NewsService(repository, sources=[enabled_source, disabled_source])

    result = await service.refresh(source_names={"enabled"})

    enabled_source.fetch.assert_awaited_once()
    disabled_source.fetch.assert_not_awaited()
    assert [source.source for source in result.sources] == ["enabled"]


def test_news_service_exposes_available_source_names():
    first_source = AsyncMock()
    first_source.name = "渠道一"
    second_source = AsyncMock()
    second_source.name = "渠道二"

    service = NewsService(AsyncMock(), sources=[first_source, second_source])

    assert service.available_source_names == ["渠道一", "渠道二"]


def test_news_service_rejects_unknown_source_names():
    source = AsyncMock()
    source.name = "已知渠道"
    service = NewsService(AsyncMock(), sources=[source])

    with pytest.raises(ValueError, match="未知新闻渠道"):
        service.select_sources({"未知渠道"})


def test_calculate_heat_scores_rewards_recent_multi_source_reporting():
    now = datetime(2026, 7, 16, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    articles = [
        {
            "source": "同花顺",
            "title": "人工智能板块快速走强",
            "published_at": now,
            "source_heat": 3,
        },
        {
            "source": "华尔街见闻",
            "title": "人工智能板块快速走强 最新消息",
            "published_at": now,
            "source_heat": 2,
        },
        {
            "source": "新浪财经",
            "title": "普通公司公告",
            "published_at": datetime(
                2026, 7, 15, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai")
            ),
            "source_heat": 0,
        },
    ]

    calculate_heat_scores(articles, now=now)

    assert articles[0]["heat_score"] > articles[2]["heat_score"]
    assert articles[1]["heat_score"] > articles[2]["heat_score"]
    assert 0 <= articles[0]["heat_score"] <= 100
