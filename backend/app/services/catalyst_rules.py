"""催化雷达规则分类器（纯函数，无 IO）。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

REPLAY_WINDOW_DAYS = 14
JACCARD_THRESHOLD = 0.55

POLICY_KEYWORDS: tuple[str, ...] = (
    "国务院",
    "发改委",
    "证监会",
    "央行",
    "工信部",
    "财政部",
    "政策",
    "意见稿",
    "规划",
    "监管",
    "部委",
)

COMPANY_KEYWORDS: tuple[str, ...] = (
    "公告",
    "业绩",
    "中标",
    "订单",
    "回购",
    "增持",
    "减持",
    "签约",
    "落地",
    "公司",
)

POLICY_SOURCE_HINTS: tuple[str, ...] = (
    "人民日报",
    "新华社",
    "gov.cn",
    "证监会",
    "发改委",
    "工信部",
    "财政部",
    "央行",
)

COMPANY_SOURCE_HINTS: tuple[str, ...] = (
    "公告",
    "上市公司",
    "巨潮",
    "上交所",
    "深交所",
)


@dataclass(frozen=True)
class EventInput:
    """规则分类输入：当前事件及同题材上下文。"""

    title: str
    published_at: datetime
    theme_id: int
    source: str = ""
    event_key: str | None = None
    summary: str = ""


@dataclass(frozen=True)
class ClassifyResult:
    """规则分类输出。"""

    freshness: str
    actor_type: str
    confidence: int
    rationale: str


def normalize_title(title: str) -> str:
    """规范化标题：去空白与标点，小写，保留中英文数字。"""
    normalized = title.strip().lower()
    return re.sub(r"[^\w]", "", normalized, flags=re.UNICODE)


def title_jaccard(a: str, b: str) -> float:
    """规范化标题字符集 Jaccard 相似度。"""
    tokens_a = set(normalize_title(a))
    tokens_b = set(normalize_title(b))
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)
    return intersection / union if union else 0.0


def _count_keyword_hits(text: str, keywords: tuple[str, ...]) -> int:
    return sum(1 for keyword in keywords if keyword in text)


def _source_hint(source: str) -> str | None:
    for hint in POLICY_SOURCE_HINTS:
        if hint in source:
            return "policy"
    for hint in COMPANY_SOURCE_HINTS:
        if hint in source:
            return "company"
    return None


def _within_replay_window(current: EventInput, recent: EventInput) -> bool:
    if recent.theme_id != current.theme_id:
        return False
    if recent.published_at >= current.published_at:
        return False
    delta = current.published_at - recent.published_at
    return delta <= timedelta(days=REPLAY_WINDOW_DAYS)


def _detect_replay(
    current: EventInput, recent_same_theme: list[EventInput]
) -> tuple[bool, str, float]:
    best_jaccard = 0.0
    for recent in recent_same_theme:
        if not _within_replay_window(current, recent):
            continue
        if (
            current.event_key
            and recent.event_key
            and current.event_key == recent.event_key
        ):
            days = (current.published_at - recent.published_at).days
            return True, f"同 event_key，{days} 日前已有相似事件", 0.9
        score = title_jaccard(current.title, recent.title)
        if score > best_jaccard:
            best_jaccard = score
        if score >= JACCARD_THRESHOLD:
            days = (current.published_at - recent.published_at).days
            return (
                True,
                f"标题 Jaccard {score:.2f}≥{JACCARD_THRESHOLD}，{days} 日前已有相似事件",
                score,
            )
    return False, "", best_jaccard


def _classify_actor(current: EventInput) -> tuple[str, int, str]:
    text = f"{current.title} {current.summary}"
    policy_hits = _count_keyword_hits(text, POLICY_KEYWORDS)
    company_hits = _count_keyword_hits(text, COMPANY_KEYWORDS)
    source = _source_hint(current.source)

    if policy_hits == 0 and company_hits == 0:
        if source == "policy":
            return "policy", 55, "来源偏政策"
        if source == "company":
            return "company", 55, "来源偏公司"
        return "unknown", 40, "无政策/公司关键词或来源信号"

    if policy_hits > 0 and company_hits == 0:
        confidence = min(60 + policy_hits * 10, 90)
        return "policy", confidence, f"命中 {policy_hits} 个政策关键词"

    if company_hits > 0 and policy_hits == 0:
        confidence = min(60 + company_hits * 10, 90)
        return "company", confidence, f"命中 {company_hits} 个公司关键词"

    if source == "policy":
        return "policy", 65, "政策与公司词冲突，来源偏政策"
    if source == "company":
        return "company", 65, "政策与公司词冲突，来源偏公司"
    if policy_hits > company_hits:
        return (
            "policy",
            60,
            f"政策与公司词冲突，政策词 {policy_hits} > 公司词 {company_hits}",
        )
    if company_hits > policy_hits:
        return (
            "company",
            60,
            f"政策与公司词冲突，公司词 {company_hits} > 政策词 {policy_hits}",
        )
    return "other", 55, "政策与公司词冲突且信号平局"


def classify_event(
    current: EventInput, recent_same_theme: list[EventInput]
) -> ClassifyResult:
    """对单条驱动事件做新鲜度与主体类型规则分类。"""
    is_replay, replay_rationale, replay_score = _detect_replay(
        current, recent_same_theme
    )
    actor_type, actor_confidence, actor_rationale = _classify_actor(current)

    if is_replay:
        freshness = "replay"
        freshness_confidence = int(70 + replay_score * 20)
        rationale = replay_rationale
    else:
        freshness = "new"
        freshness_confidence = 70
        rationale = "未命中旧闻相似规则，视为新催化"

    confidence = min(freshness_confidence, actor_confidence)
    if actor_rationale != "无政策/公司关键词或来源信号":
        rationale = f"{rationale}；{actor_rationale}"

    return ClassifyResult(
        freshness=freshness,
        actor_type=actor_type,
        confidence=confidence,
        rationale=rationale,
    )
