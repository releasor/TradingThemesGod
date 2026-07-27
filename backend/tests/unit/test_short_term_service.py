"""短线雷达服务测试。"""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.short_term import (
    INDEX_SIGNAL_CODES,
    IndexPeriodMetric,
    PeriodThemeMetric,
    STRATEGY_QUOTE_CODES,
    ShortTermService,
)


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

    async def list_index_period_snapshot_metrics(start_date: date, end_date: date):
        if start_date == end_date:
            return [
                IndexPeriodMetric(
                    trade_date=start_date,
                    rise_fall_pct=1.2,
                    up_count=60,
                    down_count=10,
                )
            ]
        return [
            IndexPeriodMetric(
                trade_date=start_date,
                rise_fall_pct=-0.8,
                up_count=10,
                down_count=60,
            )
        ]

    service._list_index_period_snapshot_metrics = (  # type: ignore[method-assign]
        list_index_period_snapshot_metrics
    )

    today = await service.get_overview(date(2026, 7, 21), "today")
    week = await service.get_overview(date(2026, 7, 21), "current_week")

    assert today.strategy_card.index_strength == "strong"
    assert week.strategy_card.index_strength == "weak"

    assert today.strategy_card.emotion_strength == "strong"
    assert today.strategy_card.primary_strategy == "连板接力"
    assert week.strategy_card.emotion_strength == "weak"
    assert week.strategy_card.primary_strategy == "老龙抱团或空仓"
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
    service._list_index_period_snapshot_metrics = AsyncMock(return_value=[])  # type: ignore[method-assign]

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
    service._list_index_period_snapshot_metrics = AsyncMock(return_value=[])  # type: ignore[method-assign]

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
    service._list_index_period_snapshot_metrics = AsyncMock(return_value=[])  # type: ignore[method-assign]

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
    # 自定义区间仅读库，避免按日全量补快照拖垮切换体验
    service._ensure_period_snapshots.assert_not_awaited()


@pytest.mark.asyncio
async def test_analyze_from_database_skips_external_snapshot_refresh():
    service = ShortTermService(AsyncMock())
    overview = SimpleNamespace(
        strategy_card=SimpleNamespace(
            title="指数情绪策略卡",
            index_strength="strong",
            emotion_strength="strong",
            primary_strategy="连板接力",
            secondary_strategy="首板",
            rationale=[],
        ),
        market_emotion="情绪强",
        risk_signals=[],
    )
    service.get_overview = AsyncMock(return_value=overview)  # type: ignore[method-assign]
    service._review_writer = MagicMock(side_effect=RuntimeError("no db"))  # type: ignore[method-assign]

    await service.analyze_from_database(date(2026, 7, 21), "today")

    service.get_overview.assert_awaited_once()
    call_kwargs = service.get_overview.await_args.kwargs
    assert call_kwargs.get("ensure_snapshots") is False


def _mock_review_track(mock_ctx: AsyncMock | MagicMock | None = None):
    mock_writer = MagicMock()
    mock_ctx = mock_ctx or AsyncMock()
    track_cm = MagicMock()
    track_cm.__aenter__ = AsyncMock(return_value=mock_ctx)
    track_cm.__aexit__ = AsyncMock(return_value=False)
    mock_writer.track = MagicMock(return_value=track_cm)
    return mock_writer, mock_ctx


@pytest.mark.asyncio
async def test_analyze_from_database_calls_review_track():
    service = ShortTermService(AsyncMock())
    overview = SimpleNamespace(
        strategy_card=SimpleNamespace(
            title="指数情绪策略卡",
            index_strength="strong",
            emotion_strength="strong",
            primary_strategy="连板接力",
            secondary_strategy="首板",
            rationale=["依据1"],
        ),
        market_emotion="情绪强",
        risk_signals=["指数承压"],
    )
    service.get_overview = AsyncMock(return_value=overview)  # type: ignore[method-assign]
    mock_writer, mock_ctx = _mock_review_track()
    service._review_writer = MagicMock(return_value=mock_writer)  # type: ignore[method-assign]

    result = await service.analyze_from_database(date(2026, 7, 21), "today")

    mock_writer.track.assert_called_once()
    assert mock_writer.track.call_args.kwargs["run_type"] == "overview_analyze"
    mock_ctx.emit_strategy_card.assert_awaited_once()
    mock_ctx.emit_emotion.assert_awaited_once()
    assert result is overview


@pytest.mark.asyncio
async def test_analyze_swallows_review_emit_errors():
    service = ShortTermService(AsyncMock())
    overview = SimpleNamespace(
        strategy_card=SimpleNamespace(
            title="指数情绪策略卡",
            index_strength="strong",
            emotion_strength="strong",
            primary_strategy="连板接力",
            secondary_strategy="首板",
            rationale=[],
        ),
        market_emotion="情绪强",
        risk_signals=[],
    )
    service.get_overview = AsyncMock(return_value=overview)  # type: ignore[method-assign]
    mock_writer, mock_ctx = _mock_review_track()
    mock_ctx.emit_strategy_card = AsyncMock(side_effect=RuntimeError("emit boom"))
    service._review_writer = MagicMock(return_value=mock_writer)  # type: ignore[method-assign]

    result = await service.analyze_from_database(date(2026, 7, 21), "today")

    assert result is overview


@pytest.mark.asyncio
async def test_refresh_signals_calls_review_track():
    session = AsyncMock()
    session.commit = AsyncMock()
    stock = MagicMock()
    stock.code = "000001"
    stock.id = 11
    scalars_result = MagicMock()
    scalars_result.all.return_value = [stock]
    session.scalars = AsyncMock(return_value=scalars_result)
    session.execute = AsyncMock(return_value=MagicMock(all=lambda: []))
    session.add = MagicMock()

    service = ShortTermService(session)
    mock_writer, mock_ctx = _mock_review_track()
    service._review_writer = MagicMock(return_value=mock_writer)  # type: ignore[method-assign]

    from app.scrapers.dragon_tiger import SourceResult as DragonResult
    from app.scrapers.short_term_signals import SourceResult as SignalResult

    class FakeSignalScraper:
        async def fetch(self, _trade_date):
            return SignalResult(
                success=True,
                items=[
                    {
                        "trade_date": date(2026, 7, 25),
                        "stock_code": "000001",
                        "signal_type": "limit_up",
                        "streak_days": 1,
                        "open_board_count": 0,
                        "is_one_word": False,
                        "is_failed": False,
                        "source": "test",
                    }
                ],
            )

    class FakeDragonScraper:
        async def fetch(self, _trade_date):
            return DragonResult(success=True, items=[])

    from app.services import short_term as short_term_mod

    class FakeSector:
        def __init__(self, _session):
            pass

        async def rebuild(self, _trade_date, **_kwargs):
            return 0

    short_term_mod.SectorRotationService = FakeSector

    class FakeRepo:
        def __init__(self, _session):
            self.run = MagicMock()

        async def create_run(self, _trade_date):
            return self.run

        async def upsert_signals(self, _items):
            return len(_items)

        async def upsert_dragon_tiger_entries(self, _items):
            return 0

        async def get_candidates(self, _trade_date, strategy="first_to_second"):
            return []

        async def finish_run(self, *_args, **_kwargs):
            return None

    short_term_mod.ShortTermSignalRepository = FakeRepo

    with patch(
        "app.services.mining.MiningService.ensure",
        new=AsyncMock(return_value=SimpleNamespace(card_count=0)),
    ):
        result = await service.refresh_signals(
            date(2026, 7, 25),
            signal_scraper=FakeSignalScraper(),
            dragon_scraper=FakeDragonScraper(),
        )

    mock_writer.track.assert_called_once()
    assert mock_writer.track.call_args.kwargs["run_type"] == "signals_refresh"
    mock_ctx.emit_signal_batch.assert_awaited_once()
    assert result.status == "success"
    assert result.signal_count == 1


@pytest.mark.asyncio
async def test_refresh_data_calls_review_track():
    service = ShortTermService(AsyncMock())
    overview = SimpleNamespace(
        strategy_card=SimpleNamespace(
            title="指数情绪策略卡",
            index_strength="strong",
            emotion_strength="strong",
            primary_strategy="连板接力",
            secondary_strategy="首板",
            rationale=["依据1"],
        ),
        market_emotion="情绪强",
        risk_signals=[],
        missing_sources=[],
        model_copy=lambda **_kwargs: overview,
    )
    service._refresh_strategy_quotes = AsyncMock()  # type: ignore[method-assign]
    service._ensure_strategy_snapshots = AsyncMock()  # type: ignore[method-assign]
    service._persist_index_quote_snapshots = AsyncMock()  # type: ignore[method-assign]
    service._build_overview = AsyncMock(return_value=overview)  # type: ignore[method-assign]
    service._last_quote_refresh = SimpleNamespace(
        trade_date=date(2026, 7, 21),
        updated_count=9,
        source="eastmoney",
        elapsed_ms=100,
        attempts=("东方财富",),
    )
    mock_writer, mock_ctx = _mock_review_track()
    service._review_writer = MagicMock(return_value=mock_writer)  # type: ignore[method-assign]

    result = await service.refresh_data_and_get_overview(date(2026, 7, 21), "today")

    mock_writer.track.assert_called_once()
    assert mock_writer.track.call_args.kwargs["run_type"] == "quote_refresh"
    mock_ctx.emit_quote_refresh.assert_awaited_once()
    mock_ctx.emit_strategy_card.assert_awaited_once()
    assert result is overview


@pytest.mark.asyncio
async def test_refresh_data_uses_lightweight_quote_refresh_for_latest_day():
    service = ShortTermService(AsyncMock())
    service._refresh_strategy_quotes = AsyncMock()  # type: ignore[method-assign]
    service._ensure_strategy_snapshots = AsyncMock()  # type: ignore[method-assign]
    service._build_overview = AsyncMock(  # type: ignore[method-assign]
        return_value=SimpleNamespace(strategy_card=SimpleNamespace())
    )
    async def passthrough(**kwargs):
        return await kwargs["fn"](None)

    service._run_with_review_track = passthrough  # type: ignore[method-assign]

    await service.refresh_data_and_get_overview(date(2026, 7, 21), "current_month")

    service._refresh_strategy_quotes.assert_awaited_once()
    service._ensure_strategy_snapshots.assert_awaited_once_with(
        date(2026, 7, 21), STRATEGY_QUOTE_CODES
    )


@pytest.mark.asyncio
async def test_refresh_data_skips_snapshots_for_today():
    service = ShortTermService(AsyncMock())
    service._refresh_strategy_quotes = AsyncMock()  # type: ignore[method-assign]
    service._ensure_strategy_snapshots = AsyncMock()  # type: ignore[method-assign]
    overview = MagicMock()
    overview.model_copy.return_value = overview
    service._build_overview = AsyncMock(return_value=overview)  # type: ignore[method-assign]
    async def passthrough(**kwargs):
        return await kwargs["fn"](None)

    service._run_with_review_track = passthrough  # type: ignore[method-assign]

    await service.refresh_data_and_get_overview(date(2026, 7, 21), "today")

    service._ensure_strategy_snapshots.assert_not_awaited()


@pytest.mark.asyncio
async def test_refresh_strategy_quotes_only_updates_strategy_theme_codes(monkeypatch):
    service = ShortTermService(AsyncMock())
    captured: dict[str, object] = {}

    async def fake_refresh(codes):
        captured["only_codes"] = codes
        return SimpleNamespace(
            trade_date=date(2026, 7, 23),
            source="eastmoney",
            elapsed_ms=1200,
            attempts=("东方财富",),
            updated_count=len(codes),
        )

    monkeypatch.setattr(
        "app.services.short_term.refresh_strategy_quotes",
        fake_refresh,
    )

    await service._refresh_strategy_quotes()

    assert captured["only_codes"] == STRATEGY_QUOTE_CODES


def test_period_index_score_averages_daily_board_returns():
    metrics = [
        IndexPeriodMetric(date(2026, 7, 21), 1.0, 0, 0),
        IndexPeriodMetric(date(2026, 7, 21), 0.2, 0, 0),
        IndexPeriodMetric(date(2026, 7, 22), -1.0, 0, 0),
        IndexPeriodMetric(date(2026, 7, 22), -0.4, 0, 0),
    ]

    score = ShortTermService._period_index_score(metrics)

    assert score == pytest.approx(-0.05)


def test_period_index_score_uses_breadth_proxy_when_pct_missing():
    metrics = [
        IndexPeriodMetric(date(2026, 7, 21), None, 80, 20),
        IndexPeriodMetric(date(2026, 7, 21), None, 70, 30),
    ]

    score = ShortTermService._period_index_score(metrics)

    assert score == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_resolve_index_score_prefers_live_for_today():
    live = [
        SimpleNamespace(rise_fall_pct=Decimal("0.9")),
        SimpleNamespace(rise_fall_pct=Decimal("0.7")),
    ]
    period = [IndexPeriodMetric(date(2026, 7, 21), -0.5, 0, 0)]

    score = ShortTermService._resolve_index_score(
        date(2026, 7, 21),
        date(2026, 7, 21),
        live,
        period,
    )

    assert score == pytest.approx(0.8)


@pytest.mark.asyncio
async def test_resolve_index_score_prefers_period_for_multi_day():
    live = [SimpleNamespace(rise_fall_pct=Decimal("1.2"))]
    period = [IndexPeriodMetric(date(2026, 7, 21), -0.6, 0, 0)]

    score = ShortTermService._resolve_index_score(
        date(2026, 7, 14),
        date(2026, 7, 21),
        live,
        period,
    )

    assert score == pytest.approx(-0.6)


@pytest.mark.asyncio
async def test_ensure_period_snapshots_still_backfills_index_when_theme_days_exist():
    """题材快照已齐时，仍应补齐缺失的指数板块快照。"""
    session = AsyncMock()
    # 周期内工作日均已有题材快照，但指数板可能缺失
    session.execute = AsyncMock(
        return_value=SimpleNamespace(
            scalars=lambda: SimpleNamespace(
                all=lambda: [
                    date(2026, 7, 20),
                    date(2026, 7, 21),
                    date(2026, 7, 22),
                    date(2026, 7, 23),
                    date(2026, 7, 24),
                ]
            )
        )
    )
    service = ShortTermService(session)
    service._ensure_index_period_snapshots = AsyncMock()  # type: ignore[method-assign]

    await service._ensure_period_snapshots(date(2026, 7, 20), date(2026, 7, 24))

    service._ensure_index_period_snapshots.assert_awaited_once_with(
        date(2026, 7, 20), date(2026, 7, 24)
    )


@pytest.mark.asyncio
async def test_overview_flags_incomplete_index_period_snapshots():
    service = ShortTermService(AsyncMock())
    service._list_themes_by_codes = AsyncMock(return_value=[])  # type: ignore[method-assign]
    service._list_leading_themes = AsyncMock(return_value=[])  # type: ignore[method-assign]
    service._ensure_period_snapshots = AsyncMock()  # type: ignore[method-assign]
    service._list_period_snapshot_metrics = AsyncMock(return_value=[])  # type: ignore[method-assign]
    service._list_index_period_snapshot_metrics = AsyncMock(  # type: ignore[method-assign]
        return_value=[
            IndexPeriodMetric(date(2026, 7, 20), -1.0, 10, 90),
            IndexPeriodMetric(date(2026, 7, 24), -2.0, 5, 95),
        ]
    )

    overview = await service.get_overview(date(2026, 7, 24), "current_month")

    assert "指数周期快照不完整" in overview.missing_sources
    assert overview.degraded is True


def test_resolve_trade_date_rolls_weekend_to_previous_friday(monkeypatch):
    """非交易日（周末）一律回退到上一周五，含显式传入与未指定。"""
    from app.services.trading_calendar import TradingCalendar

    TradingCalendar.clear()
    monkeypatch.setattr(
        "app.services.trading_calendar._shanghai_today",
        lambda: date(2026, 7, 26),
    )
    assert ShortTermService.resolve_trade_date(date(2026, 7, 25)) == date(2026, 7, 24)
    assert ShortTermService.resolve_trade_date(date(2026, 7, 26)) == date(2026, 7, 24)
    assert ShortTermService.resolve_trade_date(None) == date(2026, 7, 24)
    assert ShortTermService.resolve_trade_date(date(2026, 7, 24)) == date(2026, 7, 24)


def test_resolve_trade_date_uses_trading_calendar_holidays():
    from app.services.trading_calendar import TradingCalendar

    TradingCalendar.load_dates({date(2026, 9, 30), date(2026, 10, 8)})
    try:
        assert ShortTermService.resolve_trade_date(date(2026, 10, 1)) == date(2026, 9, 30)
    finally:
        TradingCalendar.clear()


@pytest.mark.asyncio
async def test_overview_without_trade_date_uses_resolved_weekday(monkeypatch):
    """未指定交易日时，周末应回退，避免当日快照为空触发「周期市场快照」缺失。"""
    service = ShortTermService(AsyncMock())
    service._list_themes_by_codes = AsyncMock(return_value=[])  # type: ignore[method-assign]
    service._list_leading_themes = AsyncMock(  # type: ignore[method-assign]
        return_value=[
            SimpleNamespace(
                rise_fall_pct=Decimal("1"), heat_index=Decimal("50"), stock_count=1
            )
        ]
    )
    service._ensure_period_snapshots = AsyncMock()  # type: ignore[method-assign]
    service._list_period_snapshot_metrics = AsyncMock(  # type: ignore[method-assign]
        return_value=[
            PeriodThemeMetric(
                rise_fall_pct=1.0,
                heat_index=50.0,
                stock_count=10,
                up_count=5,
                down_count=5,
                limit_up_count=2,
                limit_down_count=0,
                trading_days=1,
            )
        ]
    )
    service._list_index_period_snapshot_metrics = AsyncMock(return_value=[])  # type: ignore[method-assign]

    class _FakeDate(date):
        @classmethod
        def today(cls):
            return date(2026, 7, 25)  # Saturday

    monkeypatch.setattr("app.services.short_term.date", _FakeDate)

    overview = await service.get_overview(period="today")

    assert overview.trade_date == date(2026, 7, 24)
    assert overview.end_date == date(2026, 7, 24)
    assert "周期市场快照" not in overview.missing_sources
    service._list_period_snapshot_metrics.assert_awaited()
    assert service._list_period_snapshot_metrics.await_args.args[:2] == (
        date(2026, 7, 24),
        date(2026, 7, 24),
    )
