"""题材挖掘规则引擎测试。"""

from app.services.mining_rules import (
    CardDraft,
    StockMetric,
    ThemeMiningInput,
    mine_theme,
)


def _stock(
    stock_id: int,
    rise_fall_pct: float | None,
    *,
    heat: float | None = None,
    name: str | None = None,
) -> StockMetric:
    return StockMetric(
        stock_id=stock_id,
        rise_fall_pct=rise_fall_pct,
        heat=heat,
        name=name,
    )


def _input(
    stocks: list[StockMetric],
    *,
    theme_id: int = 1,
    lifecycle_stage: str = "fermentation",
    strength_score: int = 60,
    leader_clarity_score: int | None = 55,
    flow_score: int | None = 50,
) -> ThemeMiningInput:
    return ThemeMiningInput(
        theme_id=theme_id,
        lifecycle_stage=lifecycle_stage,
        strength_score=strength_score,
        leader_clarity_score=leader_clarity_score,
        flow_score=flow_score,
        stocks=stocks,
    )


def _card(cards: list[CardDraft], mining_type: str) -> CardDraft | None:
    return next((card for card in cards if card.mining_type == mining_type), None)


def test_low_branch_emits_laggards_below_40th_percentile():
    stocks = [
        _stock(1, 8.0),
        _stock(2, 6.0),
        _stock(3, 4.0),
        _stock(4, 1.0),
        _stock(5, -2.0),
    ]
    cards = mine_theme(_input(stocks))

    card = _card(cards, "low_branch")
    assert card is not None
    assert len(card.members) >= 2
    assert all(member.role_tag == "laggard" for member in card.members)
    member_ids = {member.stock_id for member in card.members}
    assert 4 in member_ids
    assert 5 in member_ids
    assert 1 not in member_ids


def test_low_branch_requires_at_least_two_members():
    stocks = [
        _stock(1, 5.0),
        _stock(2, 4.8),
        _stock(3, 4.5),
    ]
    cards = mine_theme(_input(stocks, strength_score=70))

    assert _card(cards, "low_branch") is None


def test_low_branch_skipped_in_ebb_stage():
    stocks = [
        _stock(1, 5.0),
        _stock(2, 4.0),
        _stock(3, 1.0),
        _stock(4, -1.0),
    ]
    cards = mine_theme(_input(stocks, lifecycle_stage="ebb", strength_score=70))

    assert _card(cards, "low_branch") is None


def test_catch_up_emits_positive_risers_below_median():
    stocks = [
        _stock(1, 9.0),
        _stock(2, 7.0),
        _stock(3, 3.0),
        _stock(4, 1.5),
        _stock(5, -1.0),
    ]
    cards = mine_theme(_input(stocks, lifecycle_stage="climax"))

    card = _card(cards, "catch_up")
    assert card is not None
    assert all(member.role_tag == "starter" for member in card.members)
    member_ids = {member.stock_id for member in card.members}
    assert 3 in member_ids
    assert 4 in member_ids
    assert 1 not in member_ids


def test_catch_up_skipped_when_stage_not_strong():
    stocks = [
        _stock(1, 8.0),
        _stock(2, 5.0),
        _stock(3, 2.0),
        _stock(4, 1.0),
    ]
    cards = mine_theme(_input(stocks, lifecycle_stage="germination"))

    assert _card(cards, "catch_up") is None


def test_hidden_leader_excludes_top_two_risers():
    stocks = [
        _stock(1, 10.0, heat=30),
        _stock(2, 9.0, heat=25),
        _stock(3, 6.5, heat=95, name="细分龙头A"),
        _stock(4, 5.0, heat=80),
        _stock(5, 2.0, heat=40),
    ]
    cards = mine_theme(_input(stocks))

    card = _card(cards, "hidden_leader")
    assert card is not None
    assert all(member.role_tag == "shadow_leader" for member in card.members)
    member_ids = {member.stock_id for member in card.members}
    assert 1 not in member_ids
    assert 2 not in member_ids
    assert 3 in member_ids


def test_hidden_leader_degraded_when_snapshot_scores_missing():
    stocks = [
        _stock(1, 10.0),
        _stock(2, 8.0),
        _stock(3, 6.0, heat=90),
        _stock(4, 4.0, heat=70),
    ]
    cards = mine_theme(
        _input(stocks, leader_clarity_score=None, flow_score=None),
    )

    card = _card(cards, "hidden_leader")
    assert card is not None
    assert card.degraded is True
    assert "leader_clarity_score" in card.missing_metrics
    assert "flow_score" in card.missing_metrics


def test_missing_rise_fall_pct_emits_no_cards():
    stocks = [
        _stock(1, None),
        _stock(2, None),
        _stock(3, None),
    ]
    cards = mine_theme(_input(stocks))

    assert cards == []


def test_limit_down_anomaly_excluded_from_mining():
    stocks = [
        _stock(1, 5.0),
        _stock(2, 4.0),
        _stock(3, -10.0),
        _stock(4, -10.0),
    ]
    cards = mine_theme(_input(stocks, strength_score=70))

    low_branch = _card(cards, "low_branch")
    if low_branch is not None:
        member_ids = {member.stock_id for member in low_branch.members}
        assert 3 not in member_ids
        assert 4 not in member_ids


def test_mine_theme_returns_up_to_three_card_types():
    stocks = [
        _stock(1, 10.0, heat=20),
        _stock(2, 8.0, heat=25),
        _stock(3, 5.0, heat=90, name="隐形龙头"),
        _stock(4, 2.0, heat=60),
        _stock(5, 0.5, heat=40),
        _stock(6, -1.0, heat=30),
    ]
    cards = mine_theme(_input(stocks, lifecycle_stage="fermentation", strength_score=65))

    types = {card.mining_type for card in cards}
    assert "low_branch" in types
    assert "catch_up" in types
    assert "hidden_leader" in types
    assert len(cards) == 3
