"""主线图谱规则引擎（纯函数，无 IO）。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ThemeSnap:
    """题材快照（建边输入）。"""

    theme_id: int
    mainline_score: int
    strength_score: int = 0
    lifecycle_stage: str = ""


@dataclass
class EdgeDraft:
    """规则建边草稿。"""

    from_theme_id: int
    to_theme_id: int
    weight: float
    method: str = "rules"
    status: str = "active"
    rationale: str = ""


def jaccard(a: set, b: set) -> float:
    """集合 Jaccard 相似度；空并集返回 0。"""
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _overlap_weight(
    overlap: dict[tuple[int, int], float],
    theme_a: int,
    theme_b: int,
) -> float | None:
    if (theme_a, theme_b) in overlap:
        return overlap[(theme_a, theme_b)]
    if (theme_b, theme_a) in overlap:
        return overlap[(theme_b, theme_a)]
    lo, hi = min(theme_a, theme_b), max(theme_a, theme_b)
    if (lo, hi) in overlap:
        return overlap[(lo, hi)]
    return None


def _directed_endpoints(left: ThemeSnap, right: ThemeSnap) -> tuple[int, int]:
    """高 mainline_score 为 from；平局取较小 theme_id 为 from。"""
    if left.mainline_score > right.mainline_score:
        return left.theme_id, right.theme_id
    if right.mainline_score > left.mainline_score:
        return right.theme_id, left.theme_id
    if left.theme_id < right.theme_id:
        return left.theme_id, right.theme_id
    return right.theme_id, left.theme_id


def build_edges(
    themes: list[ThemeSnap],
    overlap: dict[tuple[int, int], float],
    *,
    jaccard_min: float = 0.12,
    top_main: int = 5,
) -> list[EdgeDraft]:
    """按主线 Top-K 与成分股重叠建有向边。

    - 前 ``top_main``（按 mainline_score 降序，平局 theme_id 升序）参与主线配对
    - 仅对「至少一个端点属于 Top-K」的题材对建边
    - Jaccard ≥ 阈值时建边，weight=Jaccard；from=更高 mainline_score
    """
    if not themes or top_main <= 0:
        return []

    ordered = sorted(
        themes,
        key=lambda item: (-item.mainline_score, item.theme_id),
    )
    mainline_ids = {item.theme_id for item in ordered[:top_main]}
    by_id = {item.theme_id: item for item in themes}

    edges: list[EdgeDraft] = []
    seen_pairs: set[tuple[int, int]] = set()

    for i, left in enumerate(ordered):
        for right in ordered[i + 1 :]:
            if (
                left.theme_id not in mainline_ids
                and right.theme_id not in mainline_ids
            ):
                continue
            pair_key = (
                min(left.theme_id, right.theme_id),
                max(left.theme_id, right.theme_id),
            )
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            weight = _overlap_weight(overlap, left.theme_id, right.theme_id)
            if weight is None or weight < jaccard_min:
                continue

            from_id, to_id = _directed_endpoints(
                by_id[left.theme_id], by_id[right.theme_id]
            )
            edges.append(
                EdgeDraft(
                    from_theme_id=from_id,
                    to_theme_id=to_id,
                    weight=float(weight),
                    method="rules",
                    status="active",
                    rationale=f"Jaccard={weight:.4f}",
                )
            )

    return edges


def assign_roles(
    themes: list[ThemeSnap],
    *,
    top_main: int = 5,
) -> dict[int, str]:
    """返回 theme_id → role（mainline / branch）。"""
    ordered = sorted(
        themes,
        key=lambda item: (-item.mainline_score, item.theme_id),
    )
    roles: dict[int, str] = {}
    for index, item in enumerate(ordered):
        roles[item.theme_id] = "mainline" if index < top_main else "branch"
    return roles
