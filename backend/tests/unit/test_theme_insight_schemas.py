"""题材洞察响应契约测试。"""

from datetime import UTC, date, datetime

from app.schemas.theme import ThemeDetailResponse
from app.schemas.theme_insight import ThemeMarketSnapshotResponse


def test_market_snapshot_ratio_is_null_when_down_count_is_zero():
    snapshot = ThemeMarketSnapshotResponse(
        trade_date=date(2026, 7, 20),
        up_count=12,
        down_count=0,
        flat_count=1,
        suspended_count=2,
        limit_up_count=3,
        limit_down_count=0,
        calculated_at=datetime.now(UTC),
    )

    assert snapshot.up_down_ratio is None
    assert snapshot.up_down_display == "12:0"


def test_market_snapshot_calculates_ratio_when_down_count_is_nonzero():
    snapshot = ThemeMarketSnapshotResponse(
        trade_date=date(2026, 7, 20),
        up_count=12,
        down_count=8,
        flat_count=1,
        suspended_count=2,
        limit_up_count=None,
        limit_down_count=None,
        calculated_at=datetime.now(UTC),
    )

    assert snapshot.up_down_ratio == 1.5
    assert snapshot.up_down_display == "12:8"


def test_theme_detail_insight_fields_have_backward_compatible_defaults():
    fields = ThemeDetailResponse.model_fields

    assert fields["profile"].default is None
    assert fields["market_snapshot"].default is None
    assert fields["recent_driver_events"].default_factory() == []
