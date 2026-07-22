"""短线雷达响应模型测试。"""

from datetime import date

from app.schemas.short_term import (
    FirstToSecondCandidateItem,
    FirstToSecondCandidateResponse,
    MarketStrategyCardResponse,
    ShortTermOverviewResponse,
)


def test_overview_response_contains_market_strategy_card():
    response = ShortTermOverviewResponse(
        trade_date=date(2026, 7, 21),
        period="today",
        period_label="当日",
        start_date=date(2026, 7, 21),
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

    payload = response.model_dump(mode="json")

    assert payload["strategy_card"]["primary_strategy"] == "连板接力"
    assert payload["strategy_card"]["secondary_strategy"] == "主升分歧接力"
    assert payload["period"] == "today"
    assert payload["period_label"] == "当日"
    assert payload["start_date"] == "2026-07-21"
    assert payload["end_date"] == "2026-07-21"


def test_overview_response_accepts_custom_period():
    response = ShortTermOverviewResponse(
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

    assert response.period == "custom"
    assert response.period_label == "自定义"


def test_first_to_second_candidate_response_serializes_real_stock_fields():
    response = FirstToSecondCandidateResponse(
        trade_date=date(2026, 7, 21),
        previous_trade_date=date(2026, 7, 20),
        refreshed_at="2026-07-21T10:30:00Z",
        degraded=True,
        missing_sources=["model_catalyst"],
        candidates=[
            FirstToSecondCandidateItem(
                code="000001",
                name="平安银行",
                theme_name="金融科技",
                price=12.3,
                market_cap=120.0,
                float_market_cap=60.0,
                turnover_rate=8.5,
                amount=9.2,
                first_limit_up_at="09:42:00",
                open_board_count=0,
                score=86,
                decision="candidate",
                matched_rules=["流通市值 20-80 亿", "今日仍在涨停池"],
                excluded_rules=[],
                risk_flags=["模型催化缺失"],
                catalysts=["行业催化：金融科技"],
                operation_advice="只做换手晋级确认。",
                core_conclusion="具备一进二观察价值。",
            )
        ],
        excluded_count=2,
        source_status={"limit_pool": "success"},
    )

    payload = response.model_dump(mode="json")

    assert payload["candidates"][0]["code"] == "000001"
    assert payload["candidates"][0]["decision"] == "candidate"
    assert payload["missing_sources"] == ["model_catalyst"]
