"""题材挖掘规则引擎（纯函数，无 IO）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

MiningType = Literal["low_branch", "catch_up", "hidden_leader"]

STRONG_STAGES = frozenset({"fermentation", "climax", "divergence"})
LOW_BRANCH_MIN_STRENGTH = 45
LOW_BRANCH_PERCENTILE = 40
LIMIT_DOWN_ANOMALY_THRESHOLD = -9.5
LEADER_KEYWORDS: tuple[str, ...] = ("龙头", "龙一", "龙二", "龙三", "总龙头")
HIDDEN_LEADER_MAX_MEMBERS = 5
CATCH_UP_MAX_MEMBERS = 8


@dataclass(frozen=True)
class StockMetric:
    """成分股指标。"""

    stock_id: int
    rise_fall_pct: float | None
    heat: float | None = None
    name: str | None = None


@dataclass(frozen=True)
class ThemeMiningInput:
    """单题材挖掘输入。"""

    theme_id: int
    lifecycle_stage: str
    strength_score: int
    leader_clarity_score: int | None
    flow_score: int | None
    stocks: list[StockMetric]


@dataclass
class MemberDraft:
    """挖掘卡成份股草稿。"""

    stock_id: int
    score: int
    rank: int
    role_tag: str
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class CardDraft:
    """挖掘卡草稿。"""

    mining_type: MiningType
    score: int
    lifecycle_stage: str
    strength_score: int
    rationale: str
    score_breakdown: dict[str, Any] = field(default_factory=dict)
    degraded: bool = False
    missing_metrics: list[str] = field(default_factory=list)
    members: list[MemberDraft] = field(default_factory=list)


def _clamp(value: float, low: float = 0, high: float = 100) -> int:
    return int(round(max(low, min(high, value))))


def _is_limit_down_anomaly(rise_fall_pct: float) -> bool:
    return rise_fall_pct <= LIMIT_DOWN_ANOMALY_THRESHOLD


def _quoted_stocks(stocks: list[StockMetric]) -> list[StockMetric]:
    return [
        stock
        for stock in stocks
        if stock.rise_fall_pct is not None and not _is_limit_down_anomaly(stock.rise_fall_pct)
    ]


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * pct / 100.0
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    if lower == upper:
        return ordered[lower]
    weight = rank - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * weight


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _count_score(member_count: int, *, cap: int = 5) -> int:
    return _clamp(member_count / cap * 100)


def _leader_keyword_bonus(name: str | None) -> int:
    if not name:
        return 0
    for keyword in LEADER_KEYWORDS:
        if keyword in name:
            return 10
    return 0


def _rank_members(
    scored: list[tuple[StockMetric, int, dict[str, Any]]],
    role_tag: str,
) -> list[MemberDraft]:
    ordered = sorted(scored, key=lambda item: item[1], reverse=True)
    members: list[MemberDraft] = []
    for index, (stock, score, metrics) in enumerate(ordered, start=1):
        members.append(
            MemberDraft(
                stock_id=stock.stock_id,
                score=score,
                rank=index,
                role_tag=role_tag,
                metrics=metrics,
            )
        )
    return members


def _mine_low_branch(inp: ThemeMiningInput, quoted: list[StockMetric]) -> CardDraft | None:
    if inp.lifecycle_stage == "ebb":
        return None
    if inp.strength_score < LOW_BRANCH_MIN_STRENGTH:
        return None

    rises = [stock.rise_fall_pct for stock in quoted if stock.rise_fall_pct is not None]
    threshold = _percentile(rises, LOW_BRANCH_PERCENTILE)
    laggards = [stock for stock in quoted if stock.rise_fall_pct is not None and stock.rise_fall_pct < threshold]
    if len(laggards) < 2:
        return None

    count_component = _count_score(len(laggards))
    card_score = _clamp(inp.strength_score * 0.5 + count_component * 0.5)
    scored: list[tuple[StockMetric, int, dict[str, Any]]] = []
    for stock in laggards:
        assert stock.rise_fall_pct is not None
        lag = max(threshold - stock.rise_fall_pct, 0.0)
        member_score = _clamp(50 + lag * 8)
        scored.append(
            (
                stock,
                member_score,
                {
                    "rise_fall_pct": stock.rise_fall_pct,
                    "theme_percentile_threshold": round(threshold, 4),
                    "lag_vs_threshold": round(lag, 4),
                },
            )
        )

    return CardDraft(
        mining_type="low_branch",
        score=card_score,
        lifecycle_stage=inp.lifecycle_stage,
        strength_score=inp.strength_score,
        rationale=f"强度{inp.strength_score}，{len(laggards)}只成份股低于{LOW_BRANCH_PERCENTILE}分位",
        score_breakdown={
            "strength_component": round(inp.strength_score * 0.5, 2),
            "count_component": round(count_component * 0.5, 2),
            "member_count": len(laggards),
            "percentile_threshold": round(threshold, 4),
        },
        members=_rank_members(scored, "laggard"),
    )


def _mine_catch_up(inp: ThemeMiningInput, quoted: list[StockMetric]) -> CardDraft | None:
    if inp.lifecycle_stage not in STRONG_STAGES:
        return None

    rises = [stock.rise_fall_pct for stock in quoted if stock.rise_fall_pct is not None]
    theme_median = _median(rises)
    ranked = sorted(
        quoted,
        key=lambda stock: stock.rise_fall_pct if stock.rise_fall_pct is not None else float("-inf"),
        reverse=True,
    )
    mid_rank = (len(ranked) + 1) // 2

    starters: list[StockMetric] = []
    for index, stock in enumerate(ranked, start=1):
        rise = stock.rise_fall_pct
        if rise is None or rise <= 0:
            continue
        below_median = rise < theme_median
        middle_to_back = index >= mid_rank
        if below_median or middle_to_back:
            starters.append(stock)

    if not starters:
        return None

    starters = starters[:CATCH_UP_MAX_MEMBERS]
    count_component = _count_score(len(starters))
    card_score = _clamp(inp.strength_score * 0.5 + count_component * 0.5)
    scored: list[tuple[StockMetric, int, dict[str, Any]]] = []
    for stock in starters:
        assert stock.rise_fall_pct is not None
        gap = max(theme_median - stock.rise_fall_pct, 0.0)
        member_score = _clamp(stock.rise_fall_pct * 6 + max(20 - gap * 3, 0))
        scored.append(
            (
                stock,
                member_score,
                {
                    "rise_fall_pct": stock.rise_fall_pct,
                    "theme_median": round(theme_median, 4),
                    "gap_to_median": round(gap, 4),
                },
            )
        )

    return CardDraft(
        mining_type="catch_up",
        score=card_score,
        lifecycle_stage=inp.lifecycle_stage,
        strength_score=inp.strength_score,
        rationale=f"阶段{inp.lifecycle_stage}，{len(starters)}只正涨且仍低于中位数",
        score_breakdown={
            "strength_component": round(inp.strength_score * 0.5, 2),
            "count_component": round(count_component * 0.5, 2),
            "theme_median": round(theme_median, 4),
            "member_count": len(starters),
        },
        members=_rank_members(scored, "starter"),
    )


def _mine_hidden_leader(inp: ThemeMiningInput, quoted: list[StockMetric]) -> CardDraft | None:
    missing: list[str] = []
    degraded = False
    if inp.leader_clarity_score is None:
        missing.append("leader_clarity_score")
        degraded = True
    if inp.flow_score is None:
        missing.append("flow_score")
        degraded = True

    ranked = sorted(
        quoted,
        key=lambda stock: stock.rise_fall_pct if stock.rise_fall_pct is not None else float("-inf"),
        reverse=True,
    )
    top_two_ids = {stock.stock_id for stock in ranked[:2]}
    candidates = [stock for stock in ranked if stock.stock_id not in top_two_ids]
    if not candidates:
        return None

    rise_values = [stock.rise_fall_pct for stock in candidates if stock.rise_fall_pct is not None]
    max_rise = max(rise_values) if rise_values else 0.0
    min_rise = min(rise_values) if rise_values else 0.0
    rise_span = max(max_rise - min_rise, 0.01)

    scored: list[tuple[StockMetric, int, dict[str, Any]]] = []
    for stock in candidates:
        rise = stock.rise_fall_pct or 0.0
        rise_norm = (rise - min_rise) / rise_span * 100
        heat_norm = stock.heat if stock.heat is not None else 50.0
        keyword_bonus = _leader_keyword_bonus(stock.name)
        composite = rise_norm * 0.6 + heat_norm * 0.4 + keyword_bonus
        member_score = _clamp(composite)
        scored.append(
            (
                stock,
                member_score,
                {
                    "rise_fall_pct": stock.rise_fall_pct,
                    "rise_norm": round(rise_norm, 4),
                    "heat": stock.heat,
                    "keyword_bonus": keyword_bonus,
                },
            )
        )

    scored.sort(key=lambda item: item[1], reverse=True)
    top_scored = scored[:HIDDEN_LEADER_MAX_MEMBERS]
    if not top_scored:
        return None

    clarity = inp.leader_clarity_score if inp.leader_clarity_score is not None else 40
    flow = inp.flow_score if inp.flow_score is not None else 40
    card_score = _clamp(clarity * 0.35 + flow * 0.25 + top_scored[0][1] * 0.40)

    return CardDraft(
        mining_type="hidden_leader",
        score=card_score,
        lifecycle_stage=inp.lifecycle_stage,
        strength_score=inp.strength_score,
        rationale=f"涨幅非Top2但综合分靠前，龙头清晰度{clarity}",
        score_breakdown={
            "leader_clarity_component": round(clarity * 0.35, 2),
            "flow_component": round(flow * 0.25, 2),
            "top_member_component": round(top_scored[0][1] * 0.40, 2),
            "excluded_top2": sorted(top_two_ids),
        },
        degraded=degraded,
        missing_metrics=missing,
        members=_rank_members(top_scored, "shadow_leader"),
    )


def mine_theme(inp: ThemeMiningInput) -> list[CardDraft]:
    """对单题材运行三类挖掘规则，返回 0–3 张卡草稿。"""
    quoted = _quoted_stocks(inp.stocks)
    if not quoted:
        return []

    cards: list[CardDraft] = []
    low_branch = _mine_low_branch(inp, quoted)
    if low_branch is not None:
        cards.append(low_branch)

    catch_up = _mine_catch_up(inp, quoted)
    if catch_up is not None:
        cards.append(catch_up)

    hidden_leader = _mine_hidden_leader(inp, quoted)
    if hidden_leader is not None:
        cards.append(hidden_leader)

    return cards
