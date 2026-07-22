"""短线雷达服务测试。"""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.short_term import PeriodThemeMetric, ShortTermService


@pytest.mark.asyncio
async def test_overview_reacts_to_period_snapshot_metrics():
    service = ShortTermService(AsyncMock())
    service._list_themes_by_codes = AsyncMock(  # type: ignore[method-assign]
        return_value=[
            SimpleNamespace(
                code="BK0500",
                rise_fall_pct=Decimal("1.2"),
                heat_index=Decimal("80"),
                stock_count=10,
            )
        ]
    )
    service._list_leading_themes = AsyncMock(return_value=[])  # type: ignore[method-assign]
    service._ensure_period_snapshots = AsyncMock()  # type: ignore[method-assign]

    async def list_period_snapshot_metrics(start_date: date, end_date: date):
        if start_date == end_date:
            return [
                PeriodThemeMetric(
                    rise_fall_pct=2.0,
                    heat_index=90.0,
                    stock_count=80,
                    up_count=60,
                    down_count=10,
                    limit_up_count=35,
                    limit_down_count=0,
                )
            ]
        return [
            PeriodThemeMetric(
                rise_fall_pct=-1.0,
                heat_index=30.0,
                stock_count=80,
                up_count=10,
                down_count=60,
                limit_up_count=2,
                limit_down_count=8,
            )
        ]

    service._list_period_snapshot_metrics = list_period_snapshot_metrics  # type: ignore[method-assign]

    today = await service.get_overview(date(2026, 7, 21), "today")
    week = await service.get_overview(date(2026, 7, 21), "current_week")

    assert today.strategy_card.emotion_strength == "strong"
    assert today.strategy_card.primary_strategy == "连板接力"
    assert week.strategy_card.emotion_strength == "weak"
    assert week.strategy_card.primary_strategy == "冰点反核与切换"
    assert "周期市场快照" not in today.missing_sources


@pytest.mark.asyncio
async def test_period_emotion_uses_average_daily_limit_up_count():
    service = ShortTermService(AsyncMock())
    service._list_themes_by_codes = AsyncMock(  # type: ignore[method-assign]
        return_value=[
            SimpleNamespace(
                code="BK0500",
                rise_fall_pct=Decimal("0.8"),
                heat_index=Decimal("70"),
                stock_count=10,
            )
        ]
    )
    service._list_leading_themes = AsyncMock(return_value=[])  # type: ignore[method-assign]
    service._ensure_period_snapshots = AsyncMock()  # type: ignore[method-assign]

    async def list_period_snapshot_metrics(start_date: date, end_date: date):
        return [
            PeriodThemeMetric(
                rise_fall_pct=-1.2,
                heat_index=22.0,
                stock_count=60,
                up_count=20,
                down_count=80,
                limit_up_count=35,
                limit_down_count=5,
                trading_days=10,
            )
        ]

    service._list_period_snapshot_metrics = list_period_snapshot_metrics  # type: ignore[method-assign]

    overview = await service.get_overview(date(2026, 7, 21), "current_month")

    assert overview.strategy_card.emotion_strength == "weak"
    assert overview.strategy_card.primary_strategy == "冰点反核与切换"
    assert any("日均连板 3.5" in item for item in overview.strategy_card.rationale)


@pytest.mark.asyncio
async def test_period_emotion_does_not_sum_duplicate_theme_limit_ups():
    service = ShortTermService(AsyncMock())
    service._list_themes_by_codes = AsyncMock(  # type: ignore[method-assign]
        return_value=[
            SimpleNamespace(
                code="BK0500",
                rise_fall_pct=Decimal("1.98"),
                heat_index=Decimal("70"),
                stock_count=10,
            )
        ]
    )
    service._list_leading_themes = AsyncMock(return_value=[])  # type: ignore[method-assign]
    service._ensure_period_snapshots = AsyncMock()  # type: ignore[method-assign]

    async def list_period_snapshot_metrics(start_date: date, end_date: date):
        return [
            PeriodThemeMetric(
                rise_fall_pct=0.5,
                heat_index=30.0,
                stock_count=40,
                up_count=12,
                down_count=18,
                limit_up_count=30,
                limit_down_count=2,
                trading_days=15,
            )
            for _ in range(459)
        ]

    service._list_period_snapshot_metrics = list_period_snapshot_metrics  # type: ignore[method-assign]

    overview = await service.get_overview(date(2026, 7, 21), "current_month")

    assert any("日均连板 2.0" in item for item in overview.strategy_card.rationale)
    assert not any("905" in item for item in overview.strategy_card.rationale)
    assert overview.strategy_card.emotion_strength == "weak"


@pytest.mark.asyncio
async def test_custom_period_uses_supplied_date_range():
    service = ShortTermService(AsyncMock())
    service._list_themes_by_codes = AsyncMock(return_value=[])  # type: ignore[method-assign]
    service._list_leading_themes = AsyncMock(return_value=[])  # type: ignore[method-assign]
    service._ensure_period_snapshots = AsyncMock()  # type: ignore[method-assign]
    service._list_period_snapshot_metrics = AsyncMock(return_value=[])  # type: ignore[method-assign]

    overview = await service.get_overview(
        date(2026, 7, 21),
        "custom",
        start_date=date(2026, 7, 3),
        end_date=date(2026, 7, 17),
    )

    assert overview.period == "custom"
    assert overview.period_label == "自定义"
    assert overview.start_date == date(2026, 7, 3)
    assert overview.end_date == date(2026, 7, 17)
    service._ensure_period_snapshots.assert_awaited_once_with(
        date(2026, 7, 3), date(2026, 7, 17)
    )
