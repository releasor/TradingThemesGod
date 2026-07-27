"""催化雷达 API 测试。"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.catalyst import (
    CatalystEnsureResponse,
    CatalystFeedItem,
    CatalystFeedResponse,
    CatalystThemeSummaryResponse,
)


def _feed_item() -> CatalystFeedItem:
    return CatalystFeedItem(
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


def test_get_catalyst_feed_returns_200():
    service_response = CatalystFeedResponse(items=[_feed_item()], total=1)

    with patch("app.api.catalysts.CatalystService") as service_class:
        service = service_class.return_value
        service.get_feed = AsyncMock(return_value=service_response)

        response = TestClient(app).get(
            "/api/v1/catalysts/feed?freshness=new&actor_type=policy&limit=10"
        )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["freshness"] == "new"
    assert body["items"][0]["actor_type"] == "policy"
    service.get_feed.assert_awaited_once_with(
        freshness="new",
        actor_type="policy",
        theme_id=None,
        q=None,
        start=None,
        end=None,
        limit=10,
        offset=0,
    )


def test_get_catalyst_theme_summary_returns_200():
    service_response = CatalystThemeSummaryResponse(
        theme_id=2,
        theme_name="机器人",
        lifecycle_stage="主升",
        strength_score=85,
        counts={"new": 3, "replay": 1},
        recent_events=[_feed_item()],
        news_headlines=[],
    )

    with patch("app.api.catalysts.CatalystService") as service_class:
        service = service_class.return_value
        service.get_theme_summary = AsyncMock(return_value=service_response)

        response = TestClient(app).get("/api/v1/catalysts/themes/2/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["theme_id"] == 2
    assert body["theme_name"] == "机器人"
    assert body["counts"]["new"] == 3
    service.get_theme_summary.assert_awaited_once_with(2)


def test_ensure_catalyst_classify_returns_200():
    service_response = CatalystEnsureResponse(classified_rules=5, model_queued=False)

    with patch("app.api.catalysts.CatalystService") as service_class:
        service = service_class.return_value
        service.ensure_classify = AsyncMock(return_value=service_response)

        response = TestClient(app).post("/api/v1/catalysts/classify/ensure?days=7")

    assert response.status_code == 200
    body = response.json()
    assert body["classified_rules"] == 5
    assert body["model_queued"] is False
    service.ensure_classify.assert_awaited_once_with(
        days=7,
        use_model=False,
        user_id=None,
    )
