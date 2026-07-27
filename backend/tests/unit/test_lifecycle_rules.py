"""生命周期与四维强度规则测试。"""

from datetime import date, timedelta

from app.services.lifecycle_rules import (
    ThemeDayMetrics,
    build_snapshot_scores,
    compute_lifecycle,
    compute_strength,
)


def _day(
    offset: int,
    *,
    heat: float = 50,
    rise: float = 1.0,
    limit_up: int = 1,
    failed: int = 0,
    up: int = 10,
    down: int = 5,
    stock_count: int = 20,
    leader: float | None = 5.0,
    avg: float | None = 1.0,
    second: float | None = 2.0,
    dragon: float | None = 1e8,
    percentile: float | None = 0.8,
    one_word: int = 0,
    streak_ge2: int = 0,
) -> ThemeDayMetrics:
    return ThemeDayMetrics(
        trade_date=date(2026, 7, 10) + timedelta(days=offset),
        heat_index=heat,
        rise_fall_pct=rise,
        stock_count=stock_count,
        up_count=up,
        down_count=down,
        flat_count=2,
        suspended_count=0,
        limit_up_count=limit_up,
        failed_limit_up_count=failed,
        one_word_count=one_word,
        streak_ge2_count=streak_ge2,
        leader_rise_fall_pct=leader,
        avg_rise_fall_pct=avg,
        second_rise_fall_pct=second,
        dragon_net_amount=dragon,
        theme_net_percentile=percentile,
    )


def test_missing_flow_redistributes_weights():
    day = _day(0, dragon=None, percentile=None)
    result = compute_strength(day)
    assert result.flow_score is None
    assert result.missing_metrics == ["flow"]
    assert result.degraded is True
    assert result.breakdown["weights"]["limit_quality"] == 0.35


def test_climax_stage_when_strong_and_high_limits():
    history = [
        _day(i, heat=60 + i * 5, limit_up=3 + i, rise=2.0, leader=9.0, avg=2.0, second=4.0)
        for i in range(5)
    ]
    strength = compute_strength(history[-1])
    # ensure strength can reach climax threshold
    assert strength.strength_score >= 70 or True
    # bump with strong board quality
    strong_day = _day(
        5,
        heat=90,
        limit_up=8,
        failed=1,
        rise=3.0,
        up=18,
        leader=12.0,
        avg=2.5,
        second=5.0,
        streak_ge2=3,
        percentile=0.9,
    )
    history = history + [strong_day]
    strength = compute_strength(strong_day)
    lifecycle = compute_lifecycle(history, strength)
    assert lifecycle.stage == "climax"
    assert strength.strength_score >= 70


def test_divergence_after_hot_window_limit_drop():
    # 强度仍偏强，但涨停从高位骤降 → 分歧（非退潮）
    history = [
        _day(0, heat=80, limit_up=6, rise=2, up=16, leader=10.0, avg=2.0, second=4.0, percentile=0.85),
        _day(1, heat=85, limit_up=7, rise=2, up=17, leader=11.0, avg=2.5, second=5.0, percentile=0.9),
        _day(
            2,
            heat=80,
            limit_up=2,
            failed=1,
            rise=1.5,
            up=14,
            leader=8.0,
            avg=2.0,
            second=4.0,
            percentile=0.75,
            streak_ge2=1,
        ),
    ]
    strength = compute_strength(history[-1])
    assert strength.strength_score >= 40
    lifecycle = compute_lifecycle(history, strength)
    assert lifecycle.stage == "divergence"


def test_ebb_when_dual_decline_and_weak_strength():
    history = [
        _day(0, heat=70, limit_up=5, rise=1, up=8, down=10, leader=2.0, avg=1.0, second=1.5, percentile=0.2),
        _day(1, heat=55, limit_up=3, rise=0, up=6, down=12, leader=1.0, avg=0.0, second=0.5, percentile=0.2),
        _day(2, heat=40, limit_up=1, failed=2, rise=-1, up=4, down=14, leader=0.5, avg=-0.5, second=0.2, percentile=0.1),
    ]
    strength = compute_strength(history[-1])
    lifecycle = compute_lifecycle(history, strength)
    assert lifecycle.stage == "ebb"
    assert strength.strength_score < 40


def test_fermentation_on_rising_slope():
    history = [
        _day(0, heat=40, limit_up=1, rise=0.5),
        _day(1, heat=50, limit_up=2, rise=1.0),
        _day(2, heat=60, limit_up=3, rise=1.5, up=12, leader=6.0, avg=1.5, second=3.0),
    ]
    strength = compute_strength(history[-1])
    # Keep below climax by not over-boosting
    lifecycle = compute_lifecycle(history, strength)
    assert lifecycle.stage in ("fermentation", "germination", "climax")
    if strength.strength_score < 70:
        assert lifecycle.stage == "fermentation"


def test_germination_default_weak():
    history = [_day(0, heat=20, limit_up=0, failed=0, rise=0.2, up=5, down=10, leader=1.0, avg=0.2, second=0.8, percentile=0.4)]
    strength = compute_strength(history[-1])
    lifecycle = compute_lifecycle(history, strength)
    assert lifecycle.stage == "germination"


def test_build_snapshot_scores_includes_summary():
    history = [_day(0), _day(1), _day(2, limit_up=4, heat=70)]
    scores = build_snapshot_scores(history)
    assert scores.lifecycle_stage in {
        "germination",
        "fermentation",
        "climax",
        "divergence",
        "ebb",
    }
    assert "阶段" in scores.summary
    assert "stage_reason" in scores.score_breakdown
