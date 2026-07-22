"""题材市场统计纯函数测试。"""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

from app.domain.theme_insights import (
    MarketCounts,
    build_event_key,
    classify_market_counts,
    deduplicate_event_rows,
)


def test_classify_market_counts_handles_quotes_and_limit_pools():
    stocks = [
        SimpleNamespace(code="000001", rise_fall_pct=Decimal("2.1")),
        SimpleNamespace(code="000002", rise_fall_pct=Decimal("-1")),
        SimpleNamespace(code="000003", rise_fall_pct=Decimal("0")),
        SimpleNamespace(code="000004", rise_fall_pct=None),
    ]

    counts = classify_market_counts(stocks, {"000001"}, {"000002"})

    assert counts == MarketCounts(1, 1, 1, 1, 1, 1)


def test_classify_market_counts_preserves_unavailable_limit_pool():
    stocks = [SimpleNamespace(code="000001", rise_fall_pct=Decimal("1"))]

    counts = classify_market_counts(stocks, None, None)

    assert counts.limit_up_count is None
    assert counts.limit_down_count is None


def test_deduplicate_event_rows_merges_same_event_from_multiple_sources():
    published_at = datetime(2026, 7, 20, 8, tzinfo=UTC)
    rows = [
        {
            "title": "机器人产业政策发布！",
            "published_at": published_at,
            "url": "https://one.example/event",
        },
        {
            "title": "机器人产业政策发布",
            "published_at": published_at,
            "url": "https://two.example/news",
        },
    ]

    assert deduplicate_event_rows(rows) == [rows[0]]


def test_event_key_is_stable_across_sources_and_title_punctuation():
    first = build_event_key(
        "机器人产业政策发布！", datetime(2026, 7, 20, 1, tzinfo=UTC)
    )
    second = build_event_key("机器人产业政策发布", datetime(2026, 7, 20, 8, tzinfo=UTC))

    assert first == second
    assert first != build_event_key(
        "机器人产业政策发布", datetime(2026, 7, 21, 8, tzinfo=UTC)
    )
