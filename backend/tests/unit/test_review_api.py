"""复盘台 API 测试。"""

from datetime import date
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.review import (
    ReviewAiReportResponse,
    ReviewDayResponse,
    ReviewRunBrief,
)


def test_get_review_day_returns_200():
    service_response = ReviewDayResponse(
        trade_date=date(2026, 7, 24),
        degraded=True,
        missing_sources=["review_events"],
        runs=[
            ReviewRunBrief(
                id=1,
                trade_date=date(2026, 7, 24),
                run_type="overview_analyze",
                status="success",
                source_status={},
            )
        ],
        strategy_card={"primary_strategy": "连板接力"},
    )

    with patch("app.api.review.ReviewService") as service_class:
        service = service_class.return_value
        service.get_day = AsyncMock(return_value=service_response)

        response = TestClient(app).get("/api/v1/review/days/2026-07-24")

    assert response.status_code == 200
    body = response.json()
    assert body["trade_date"] == "2026-07-24"
    assert body["strategy_card"]["primary_strategy"] == "连板接力"
    service.get_day.assert_awaited_once_with(date(2026, 7, 24))


def test_ensure_review_report_returns_200():
    service_response = ReviewAiReportResponse(
        trade_date=date(2026, 7, 24),
        user_id=None,
        status="rule_fallback",
        content_md="# 规则摘要",
        content_json={"summary": "2026-07-24 复盘"},
    )

    with patch("app.api.review.ReviewReportService") as service_class:
        service = service_class.return_value
        service.ensure = AsyncMock(return_value=service_response)

        response = TestClient(app).post("/api/v1/review/days/2026-07-24/report/ensure")

    assert response.status_code == 200
    assert response.json()["status"] == "rule_fallback"
    service.ensure.assert_awaited_once_with(date(2026, 7, 24), None)


def test_get_review_report_returns_null_when_missing():
    with patch("app.api.review.ReviewReportService") as service_class:
        service = service_class.return_value
        service.get_report = AsyncMock(return_value=None)

        response = TestClient(app).get("/api/v1/review/days/2026-07-24/report")

    assert response.status_code == 200
    assert response.json() is None
    service.get_report.assert_awaited()


def test_list_review_days_returns_200():
    with patch("app.api.review.ReviewService") as service_class:
        service = service_class.return_value
        service.list_days = AsyncMock(
            return_value=[date(2026, 7, 23), date(2026, 7, 24)]
        )

        response = TestClient(app).get(
            "/api/v1/review/days?from=2026-07-20&to=2026-07-24"
        )

    assert response.status_code == 200
    assert response.json()["items"] == ["2026-07-23", "2026-07-24"]
    service.list_days.assert_awaited_once_with(date(2026, 7, 20), date(2026, 7, 24))
