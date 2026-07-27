"""短线雷达 API 测试。"""

from datetime import date
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.short_term import (
    FirstToSecondCandidateItem,
    FirstToSecondCandidateResponse,
    MarketStrategyCardResponse,
    ShortTermOverviewResponse,
)


def _auth_user() -> User:
    return User(id=1, username="tester", password_hash="x")


def test_short_term_overview_returns_strategy_card():
    service_response = ShortTermOverviewResponse(
        trade_date=date(2026, 7, 21),
        period="current_week",
        period_label="本周",
        start_date=date(2026, 7, 20),
        end_date=date(2026, 7, 21),
        degraded=False,
        missing_sources=[],
        market_emotion="情绪强",
        short_term_outlook="指数与情绪共振，关注主线接力。",
        operation_advice="做连板",
        tracking_focus=["连板梯队"],
        core_conclusion="优先主线前排。",
        risk_signals=[],
        sector_count=3,
        candidate_count=2,
        strategy_card=MarketStrategyCardResponse(
            title="指数情绪策略卡",
            index_strength="strong",
            emotion_strength="strong",
            primary_strategy="连板接力",
            secondary_strategy="主升分歧接力",
            operation_advice="指数强、情绪强，做连板。",
            focus_targets=["连板梯队"],
            rationale=["日均连板 28.0"],
        ),
    )

    with patch("app.api.short_term.ShortTermService") as service_class:
        service = service_class.return_value
        service.get_overview = AsyncMock(return_value=service_response)

        response = TestClient(app).get(
            "/api/v1/short-term/overview?trade_date=2026-07-21&period=current_week"
        )

    assert response.status_code == 200
    assert response.json()["period_label"] == "本周"
    assert response.json()["strategy_card"]["primary_strategy"] == "连板接力"
    service.get_overview.assert_awaited_once_with(
        date(2026, 7, 21), "current_week", start_date=None, end_date=None
    )


def test_short_term_refresh_data_triggers_live_refresh():
    service_response = ShortTermOverviewResponse(
        trade_date=date(2026, 7, 21),
        period="today",
        period_label="当日",
        start_date=date(2026, 7, 21),
        end_date=date(2026, 7, 21),
        degraded=False,
        missing_sources=[],
        market_emotion="情绪强",
        short_term_outlook="当前更适合连板接力。",
        operation_advice="做连板",
        tracking_focus=["连板梯队"],
        core_conclusion="连板接力。",
        risk_signals=[],
        sector_count=3,
        candidate_count=0,
        strategy_card=MarketStrategyCardResponse(
            title="指数情绪策略卡 · 当日",
            index_strength="strong",
            emotion_strength="strong",
            primary_strategy="连板接力",
            secondary_strategy="主升分歧接力",
            operation_advice="指数强、情绪强，做连板。",
            focus_targets=["连板梯队"],
            rationale=["指数强度 0.80"],
        ),
    )

    with patch("app.api.short_term.ShortTermService") as service_class:
        service = service_class.return_value
        service.refresh_data_and_get_overview = AsyncMock(return_value=service_response)

        response = TestClient(app).post("/api/v1/short-term/overview/refresh-data")

    assert response.status_code == 200
    service.refresh_data_and_get_overview.assert_awaited_once_with(
        None, "today", start_date=None, end_date=None
    )


def test_short_term_analyze_uses_database_only():
    service_response = ShortTermOverviewResponse(
        trade_date=date(2026, 7, 21),
        period="today",
        period_label="当日",
        start_date=date(2026, 7, 21),
        end_date=date(2026, 7, 21),
        degraded=False,
        missing_sources=[],
        market_emotion="情绪弱",
        short_term_outlook="当前更适合补涨趋势与切换。",
        operation_advice="做补涨",
        tracking_focus=["低位补涨"],
        core_conclusion="补涨趋势与切换。",
        risk_signals=["短线情绪不足"],
        sector_count=3,
        candidate_count=0,
        strategy_card=MarketStrategyCardResponse(
            title="指数情绪策略卡 · 当日",
            index_strength="strong",
            emotion_strength="weak",
            primary_strategy="补涨趋势与切换",
            secondary_strategy="轮动低吸",
            operation_advice="指数强但情绪弱，做补涨。",
            focus_targets=["低位补涨"],
            rationale=["指数强度 0.39"],
        ),
    )

    with patch("app.api.short_term.ShortTermService") as service_class:
        service = service_class.return_value
        service.analyze_from_database = AsyncMock(return_value=service_response)

        response = TestClient(app).post("/api/v1/short-term/overview/analyze")

    assert response.status_code == 200
    assert response.json()["strategy_card"]["primary_strategy"] == "补涨趋势与切换"
    service.analyze_from_database.assert_awaited_once_with(
        None, "today", start_date=None, end_date=None
    )


def test_short_term_overview_accepts_custom_date_range():
    service_response = ShortTermOverviewResponse(
        trade_date=date(2026, 7, 17),
        period="custom",
        period_label="自定义",
        start_date=date(2026, 7, 3),
        end_date=date(2026, 7, 17),
        degraded=False,
        missing_sources=[],
        market_emotion="情绪弱",
        short_term_outlook="指数强但情绪弱，关注切换。",
        operation_advice="做补涨趋势与切换",
        tracking_focus=["低位补涨"],
        core_conclusion="补涨趋势与切换。",
        risk_signals=["短线情绪不足"],
        sector_count=3,
        candidate_count=0,
        strategy_card=MarketStrategyCardResponse(
            title="指数情绪策略卡",
            index_strength="strong",
            emotion_strength="weak",
            primary_strategy="补涨趋势与切换",
            secondary_strategy="轮动低吸",
            operation_advice="指数强但情绪弱，做补涨、趋势和高低切换。",
            focus_targets=["低位补涨"],
            rationale=["日均连板 3.5"],
        ),
    )

    with patch("app.api.short_term.ShortTermService") as service_class:
        service = service_class.return_value
        service.get_overview = AsyncMock(return_value=service_response)

        response = TestClient(app).get(
            "/api/v1/short-term/overview"
            "?period=custom&start_date=2026-07-03&end_date=2026-07-17"
        )

    assert response.status_code == 200
    assert response.json()["period"] == "custom"
    assert response.json()["period_label"] == "自定义"
    service.get_overview.assert_awaited_once_with(
        None,
        "custom",
        start_date=date(2026, 7, 3),
        end_date=date(2026, 7, 17),
    )


def test_first_to_second_candidates_api_returns_live_candidates():
    service_response = FirstToSecondCandidateResponse(
        trade_date=date(2026, 7, 21),
        previous_trade_date=date(2026, 7, 20),
        refreshed_at="2026-07-21T10:30:00Z",
        degraded=False,
        missing_sources=[],
        candidates=[
            FirstToSecondCandidateItem(
                code="000001",
                name="平安银行",
                theme_name="金融科技",
                price=12.3,
                market_cap=120,
                float_market_cap=60,
                turnover_rate=8.5,
                amount=9.2,
                first_limit_up_at="09:42:00",
                open_board_count=0,
                score=86,
                decision="candidate",
                matched_rules=["今日仍在涨停池"],
                excluded_rules=[],
                risk_flags=[],
                catalysts=["行业催化：金融科技"],
                operation_advice="只做换手晋级确认。",
                core_conclusion="具备一进二观察价值。",
            )
        ],
        excluded_count=0,
        source_status={"limit_pool": "success"},
    )

    with patch("app.api.short_term.FirstToSecondService") as service_class:
        service = service_class.return_value
        service.get_candidates = AsyncMock(return_value=service_response)
        app.dependency_overrides[get_current_user] = _auth_user
        try:
            response = TestClient(app).get(
                "/api/v1/short-term/first-to-second?trade_date=2026-07-21"
            )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert response.json()["candidates"][0]["code"] == "000001"
    service.get_candidates.assert_awaited_once_with(date(2026, 7, 21), force_refresh=False)


def test_first_to_second_refresh_forces_live_candidate_refresh():
    service_response = FirstToSecondCandidateResponse(
        trade_date=date(2026, 7, 21),
        previous_trade_date=date(2026, 7, 20),
        refreshed_at="2026-07-21T10:31:00Z",
        degraded=True,
        missing_sources=["model_catalyst"],
        candidates=[],
        excluded_count=0,
        source_status={"limit_pool": "success", "model_catalyst": "missing"},
    )

    with patch("app.api.short_term.FirstToSecondService") as service_class:
        service = service_class.return_value
        service.get_candidates = AsyncMock(return_value=service_response)
        app.dependency_overrides[get_current_user] = _auth_user
        try:
            response = TestClient(app).post(
                "/api/v1/short-term/first-to-second/refresh?trade_date=2026-07-21"
            )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert response.json()["degraded"] is True
    service.get_candidates.assert_awaited_once_with(date(2026, 7, 21), force_refresh=True)
