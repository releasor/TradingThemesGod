"""题材生命周期与四维强度纯规则（无 IO）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

LifecycleStage = Literal[
    "germination", "fermentation", "climax", "divergence", "ebb"
]

CLIMAX_STRENGTH_MIN = 70
EBB_STRENGTH_MAX = 40
LIMIT_DROP_DIVERGENCE_RATIO = 0.30
NO_BOARD_QUALITY_SCORE = 25
TOP_COVER_DEFAULT = 100


@dataclass
class ThemeDayMetrics:
    trade_date: date
    heat_index: float
    rise_fall_pct: float
    stock_count: int
    up_count: int
    down_count: int
    flat_count: int
    suspended_count: int
    limit_up_count: int
    failed_limit_up_count: int
    one_word_count: int
    streak_ge2_count: int
    leader_rise_fall_pct: float | None
    avg_rise_fall_pct: float | None
    second_rise_fall_pct: float | None
    dragon_net_amount: float | None
    theme_net_percentile: float | None


@dataclass
class StrengthResult:
    strength_score: int
    limit_quality_score: int
    flow_score: int | None
    leader_clarity_score: int
    breadth_score: int
    degraded: bool
    missing_metrics: list[str] = field(default_factory=list)
    breakdown: dict[str, Any] = field(default_factory=dict)


@dataclass
class LifecycleResult:
    stage: LifecycleStage
    confidence: int
    stage_reason: str


@dataclass
class SnapshotScores:
    lifecycle_stage: LifecycleStage
    lifecycle_confidence: int
    strength_score: int
    limit_quality_score: int
    flow_score: int | None
    leader_clarity_score: int
    breadth_score: int
    mainline_score: int
    risk_score: int
    trend_score: int
    emotion_score: int
    rotation_score: int
    degraded: bool
    missing_metrics: list[str]
    score_breakdown: dict[str, Any]
    summary: str


def _clamp(value: float, low: float = 0, high: float = 100) -> int:
    return int(round(max(low, min(high, value))))


def compute_limit_quality(day: ThemeDayMetrics) -> tuple[int, dict[str, Any]]:
    success = max(day.limit_up_count, 0)
    failed = max(day.failed_limit_up_count, 0)
    total = success + failed
    if total == 0:
        return NO_BOARD_QUALITY_SCORE, {
            "mode": "no_board",
            "success": success,
            "failed": failed,
        }

    seal_rate = success / total
    score = seal_rate * 80

    if success > 0:
        streak_ratio = day.streak_ge2_count / success
        score += min(streak_ratio * 15, 15)

    if success >= 2 and day.one_word_count / success > 0.5:
        score -= 20

    return _clamp(score), {
        "mode": "board",
        "seal_rate": round(seal_rate, 4),
        "success": success,
        "failed": failed,
        "streak_ge2_count": day.streak_ge2_count,
        "one_word_count": day.one_word_count,
    }


def compute_flow(day: ThemeDayMetrics) -> tuple[int | None, dict[str, Any]]:
    if day.dragon_net_amount is None or day.theme_net_percentile is None:
        return None, {"mode": "missing"}
    # percentile 0..1 → 0..100
    return _clamp(day.theme_net_percentile * 100), {
        "mode": "percentile",
        "net_amount": day.dragon_net_amount,
        "percentile": day.theme_net_percentile,
    }


def compute_leader_clarity(day: ThemeDayMetrics) -> tuple[int, dict[str, Any]]:
    if day.leader_rise_fall_pct is None or day.avg_rise_fall_pct is None:
        return 40, {"mode": "no_quotes"}

    lead = day.leader_rise_fall_pct - day.avg_rise_fall_pct
    # 领先 0%→40，领先 8%+ → ~95
    base = 40 + max(lead, 0) * 7

    if day.second_rise_fall_pct is not None:
        gap = day.leader_rise_fall_pct - day.second_rise_fall_pct
        if gap < 1:
            base -= 15  # 群龙无首
        elif gap >= 3:
            base += 10

    return _clamp(base), {
        "mode": "lead",
        "leader": day.leader_rise_fall_pct,
        "avg": day.avg_rise_fall_pct,
        "second": day.second_rise_fall_pct,
        "lead": round(lead, 4),
    }


def compute_breadth(day: ThemeDayMetrics) -> tuple[int, dict[str, Any]]:
    active = (
        day.up_count + day.down_count + day.flat_count
    )
    if active <= 0:
        active = max(day.stock_count - day.suspended_count, 1)

    up_ratio = day.up_count / active
    denom = max(day.stock_count * 0.08, 1)
    limit_ratio = min(day.limit_up_count / denom, 1.0)
    score = (0.5 * up_ratio + 0.5 * limit_ratio) * 100
    return _clamp(score), {
        "up_ratio": round(up_ratio, 4),
        "limit_ratio": round(limit_ratio, 4),
        "active": active,
    }


def compute_strength(day: ThemeDayMetrics) -> StrengthResult:
    limit_quality, quality_meta = compute_limit_quality(day)
    flow, flow_meta = compute_flow(day)
    leader, leader_meta = compute_leader_clarity(day)
    breadth, breadth_meta = compute_breadth(day)

    missing: list[str] = []
    degraded = False
    if flow is None:
        missing.append("flow")
        degraded = True
        strength = round(limit_quality * 0.35 + leader * 0.35 + breadth * 0.30)
        weights = {"limit_quality": 0.35, "leader": 0.35, "breadth": 0.30}
    else:
        strength = round(
            limit_quality * 0.30 + flow * 0.25 + leader * 0.25 + breadth * 0.20
        )
        weights = {
            "limit_quality": 0.30,
            "flow": 0.25,
            "leader": 0.25,
            "breadth": 0.20,
        }

    return StrengthResult(
        strength_score=_clamp(strength),
        limit_quality_score=limit_quality,
        flow_score=flow,
        leader_clarity_score=leader,
        breadth_score=breadth,
        degraded=degraded,
        missing_metrics=missing,
        breakdown={
            "weights": weights,
            "limit_quality": quality_meta,
            "flow": flow_meta,
            "leader": leader_meta,
            "breadth": breadth_meta,
        },
    )


def compute_lifecycle(
    history: list[ThemeDayMetrics],
    strength: StrengthResult,
) -> LifecycleResult:
    if not history:
        return LifecycleResult("germination", 40, "无历史指标，默认萌芽")

    days = sorted(history, key=lambda d: d.trade_date)
    today = days[-1]
    window = days[-10:]
    window_len = len(window)
    confidence = 50 + min(window_len, 10) * 4
    if strength.degraded:
        confidence -= 15
    confidence = _clamp(confidence, 40, 95)

    limit_series = [d.limit_up_count for d in window]
    heat_series = [d.heat_index for d in window]
    max_limit = max(limit_series) if limit_series else 0
    recent3 = window[-3:] if len(window) >= 3 else window
    avg_recent_limit = sum(d.limit_up_count for d in recent3) / len(recent3)
    avg_recent_heat = sum(d.heat_index for d in recent3) / len(recent3)

    older = window[:-3] if len(window) > 3 else window[:1]
    avg_older_limit = sum(d.limit_up_count for d in older) / max(len(older), 1)
    avg_older_heat = sum(d.heat_index for d in older) / max(len(older), 1)

    prev_limit = days[-2].limit_up_count if len(days) >= 2 else today.limit_up_count
    limit_drop = (
        (prev_limit - today.limit_up_count) / prev_limit if prev_limit > 0 else 0.0
    )

    was_hot = any(
        d.limit_up_count >= max(2, int(max_limit * 0.6))
        or d.heat_index >= avg_older_heat * 1.1
        for d in window[:-1]
    ) if len(window) > 1 else False

    if (
        avg_recent_limit >= max(max_limit * 0.75, 2)
        and strength.strength_score >= CLIMAX_STRENGTH_MIN
        and today.rise_fall_pct > 0
    ):
        return LifecycleResult(
            "climax",
            confidence,
            f"近窗涨停高位且强度{strength.strength_score}≥{CLIMAX_STRENGTH_MIN}",
        )

    # 强度已弱且双降：优先退潮（避免被「分歧」抢先）
    if (
        avg_recent_limit < avg_older_limit
        and avg_recent_heat < avg_older_heat
        and strength.strength_score < EBB_STRENGTH_MAX
    ):
        return LifecycleResult(
            "ebb",
            confidence,
            f"涨停与热度双降且强度{strength.strength_score}<{EBB_STRENGTH_MAX}",
        )

    if was_hot and (
        limit_drop >= LIMIT_DROP_DIVERGENCE_RATIO
        or (
            today.failed_limit_up_count > today.limit_up_count
            and today.heat_index >= avg_older_heat
        )
    ):
        return LifecycleResult(
            "divergence",
            confidence,
            f"高位后涨停回落{limit_drop:.0%}或炸板升温",
        )

    if avg_recent_limit > avg_older_limit * 1.15 or avg_recent_heat > avg_older_heat * 1.1:
        if strength.strength_score < CLIMAX_STRENGTH_MIN:
            return LifecycleResult(
                "fermentation",
                confidence,
                "涨停或热度斜率向上，未达高潮阈值",
            )

    return LifecycleResult("germination", confidence, "信号偏弱，归为萌芽")


def build_snapshot_scores(history: list[ThemeDayMetrics]) -> SnapshotScores:
    if not history:
        raise ValueError("history 不能为空")

    today = sorted(history, key=lambda d: d.trade_date)[-1]
    strength = compute_strength(today)
    lifecycle = compute_lifecycle(history, strength)

    mainline = _clamp(
        strength.strength_score * 0.7
        + min(today.heat_index, 100) * 0.2
        + (10 if lifecycle.stage in ("climax", "fermentation") else 0)
    )
    risk = _clamp(
        (today.failed_limit_up_count * 8)
        + (25 if lifecycle.stage in ("ebb", "divergence") else 0)
        + (20 if strength.flow_score is not None and strength.flow_score < 35 else 0)
    )
    trend = _clamp(50 + today.rise_fall_pct * 5)
    emotion = _clamp(strength.breadth_score * 0.6 + strength.limit_quality_score * 0.4)
    rotation = _clamp((mainline + emotion) / 2)

    stage_zh = {
        "germination": "萌芽",
        "fermentation": "发酵",
        "climax": "高潮",
        "divergence": "分歧",
        "ebb": "退潮",
    }[lifecycle.stage]
    summary = (
        f"阶段{stage_zh}，强度{strength.strength_score}，"
        f"涨停{today.limit_up_count}/炸板{today.failed_limit_up_count}。"
        f"{lifecycle.stage_reason}"
    )

    return SnapshotScores(
        lifecycle_stage=lifecycle.stage,
        lifecycle_confidence=lifecycle.confidence,
        strength_score=strength.strength_score,
        limit_quality_score=strength.limit_quality_score,
        flow_score=strength.flow_score,
        leader_clarity_score=strength.leader_clarity_score,
        breadth_score=strength.breadth_score,
        mainline_score=mainline,
        risk_score=risk,
        trend_score=trend,
        emotion_score=emotion,
        rotation_score=rotation,
        degraded=strength.degraded,
        missing_metrics=list(strength.missing_metrics),
        score_breakdown={
            "stage_reason": lifecycle.stage_reason,
            "inputs": {
                "trade_date": today.trade_date.isoformat(),
                "limit_up_count": today.limit_up_count,
                "failed_limit_up_count": today.failed_limit_up_count,
                "heat_index": today.heat_index,
            },
            "weights": strength.breakdown.get("weights", {}),
            "missing_metrics": strength.missing_metrics,
            "dimensions": {
                "limit_quality": strength.breakdown.get("limit_quality"),
                "flow": strength.breakdown.get("flow"),
                "leader": strength.breakdown.get("leader"),
                "breadth": strength.breakdown.get("breadth"),
            },
        },
        summary=summary,
    )
