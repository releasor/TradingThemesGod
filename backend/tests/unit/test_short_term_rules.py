"""短线策略规则测试。"""

from app.services.short_term_rules import (
    MarketStrengthInput,
    ShortTermRuleEngine,
)


def test_market_strategy_prefers_limit_board_when_index_and_emotion_are_strong():
    engine = ShortTermRuleEngine()

    card = engine.evaluate_market_strategy(
        MarketStrengthInput(
            index_score=1.2,
            emotion_score=72,
            consecutive_board_count=28.5,
            rotation_score=66,
        )
    )

    assert card.index_strength == "strong"
    assert card.emotion_strength == "strong"
    assert card.primary_strategy == "连板接力"
    assert "做连板" in card.operation_advice
    assert "日均连板 28.5" in card.operation_advice
    assert any("日均连板 28.5" in item for item in card.rationale)


def test_market_strategy_prefers_switch_when_index_strong_and_emotion_weak():
    engine = ShortTermRuleEngine()

    card = engine.evaluate_market_strategy(
        MarketStrengthInput(
            index_score=0.8,
            emotion_score=32,
            consecutive_board_count=6,
            rotation_score=70,
        )
    )

    assert card.index_strength == "strong"
    assert card.emotion_strength == "weak"
    assert card.primary_strategy == "轮动低吸与趋势切换"
    assert "轮动低吸" in card.operation_advice
    assert "切换" in card.operation_advice
    assert card.secondary_strategy == "轮动低吸"


def test_market_strategy_context_changes_card_content_by_period_and_score():
    engine = ShortTermRuleEngine()

    card = engine.evaluate_market_strategy(
        MarketStrengthInput(
            index_score=0.8,
            emotion_score=27,
            consecutive_board_count=2.6,
            rotation_score=82,
            period_label="本周",
            index_sample_days=2,
            index_expected_days=5,
        )
    )

    assert card.title == "指数情绪策略卡 · 本周"
    assert "指数强度 0.80（本周，样本 2/5 日（快照不完整，跨周期可能数值相同））" in (
        card.rationale[0]
    )
    assert "≥ 0.3 判强" in card.formulas[0]
    assert "本次 2/5 日" in card.formulas[0]
    assert "情绪分" in card.formulas[1]
    assert "轮动分" in card.formulas[2]
    assert card.primary_strategy == "冰点反核与切换"
    assert "本周" in card.operation_advice
    assert "日均连板 2.6" in card.operation_advice
    assert "本周冰点反核" in card.focus_targets


def test_market_strategy_prefers_empty_or_old_leader_when_both_are_weak():
    engine = ShortTermRuleEngine()

    card = engine.evaluate_market_strategy(
        MarketStrengthInput(
            index_score=-0.6,
            emotion_score=18,
            consecutive_board_count=3,
            rotation_score=22,
        )
    )

    assert card.index_strength == "weak"
    assert card.emotion_strength == "weak"
    assert card.primary_strategy == "老龙抱团或空仓"
    assert card.secondary_strategy == "情绪冰点反核"
    assert "空仓更好" in card.operation_advice
