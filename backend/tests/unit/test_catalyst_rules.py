"""催化雷达规则分类器测试。"""

from datetime import datetime, timedelta, timezone

from app.services.catalyst_rules import (
    EventInput,
    classify_event,
    normalize_title,
    title_jaccard,
)

UTC = timezone.utc


def _event(
    title: str,
    *,
    days_ago: float = 0,
    theme_id: int = 1,
    source: str = "新浪财经",
    event_key: str | None = None,
) -> EventInput:
    published_at = datetime(2026, 7, 20, 12, 0, tzinfo=UTC) - timedelta(days=days_ago)
    return EventInput(
        title=title,
        published_at=published_at,
        theme_id=theme_id,
        source=source,
        event_key=event_key,
    )


def test_normalize_title_strips_punctuation_and_whitespace():
    assert normalize_title("  政策：加码机器人！ ") == normalize_title("政策加码机器人")


def test_title_jaccard_similar_titles():
    score = title_jaccard("某政策再度加码机器人", "政策加码机器人产业")
    assert score >= 0.55


def test_replay_when_title_similar_within_14_days():
    current = _event("某政策再度加码机器人")
    recent = [
        _event("政策加码机器人产业", days_ago=3),
    ]
    result = classify_event(current, recent)
    assert result.freshness == "replay"
    assert result.confidence >= 60


def test_replay_when_same_event_key_within_14_days():
    current = _event("完全不同标题A", event_key="abc123")
    recent = [
        _event("完全不同标题B", days_ago=5, event_key="abc123"),
    ]
    result = classify_event(current, recent)
    assert result.freshness == "replay"


def test_new_when_similar_title_beyond_14_days():
    current = _event("某政策再度加码机器人")
    recent = [
        _event("政策加码机器人产业", days_ago=15),
    ]
    result = classify_event(current, recent)
    assert result.freshness == "new"


def test_policy_keywords():
    current = _event("证监会发布机器人产业监管意见稿")
    result = classify_event(current, [])
    assert result.actor_type == "policy"
    assert result.confidence >= 50


def test_company_keywords():
    current = _event("某机器人公司公告中标重大订单")
    result = classify_event(current, [])
    assert result.actor_type == "company"
    assert result.confidence >= 50


def test_conflict_source_policy_wins():
    current = _event(
        "公司公告业绩同时提及监管政策",
        source="人民日报",
    )
    result = classify_event(current, [])
    assert result.actor_type == "policy"


def test_conflict_keyword_count_wins_when_no_source_hint():
    current = _event(
        "公告业绩中标订单签约落地公司发展",
        source="新浪财经",
    )
    result = classify_event(current, [])
    assert result.actor_type == "company"


def test_conflict_tie_becomes_other():
    current = _event(
        "政策规划监管公告业绩公司",
        source="新浪财经",
    )
    result = classify_event(current, [])
    assert result.actor_type == "other"


def test_unknown_when_no_signal():
    current = _event("机器人板块今日表现活跃")
    result = classify_event(current, [])
    assert result.freshness == "new"
    assert result.actor_type == "unknown"


def test_company_source_hint_without_keywords():
    current = _event("行业动态快讯", source="上市公司公告")
    result = classify_event(current, [])
    assert result.actor_type == "company"
