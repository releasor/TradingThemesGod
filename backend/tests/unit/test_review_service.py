"""ReviewService 日/题材复盘聚合与降级测试。"""

from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services.review import ReviewService


def _event(
    *,
    event_type: str,
    entity_type: str = "market",
    entity_id: int | None = None,
    payload: dict | None = None,
    run_id: int | None = 1,
):
    return SimpleNamespace(
        id=1,
        run_id=run_id,
        trade_date=date(2026, 7, 24),
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        payload_json=payload or {},
        occurred_at=datetime(2026, 7, 24, 8, 0, tzinfo=timezone.utc),
    )


def _run(*, run_id: int = 1, trade_date: date = date(2026, 7, 24)):
    return SimpleNamespace(
        id=run_id,
        trade_date=trade_date,
        run_type="overview_analyze",
        status="success",
        source_status={},
        request_meta={},
        started_at=datetime(2026, 7, 24, 7, 0, tzinfo=timezone.utc),
        finished_at=datetime(2026, 7, 24, 7, 5, tzinfo=timezone.utc),
    )


@pytest.mark.asyncio
async def test_day_review_uses_events_when_present():
    session = AsyncMock()
    service = ReviewService(session)
    service.repo = AsyncMock()
    day = date(2026, 7, 24)

    service.repo.list_events.return_value = [
        _event(
            event_type="strategy_card",
            payload={
                "title": "指数情绪策略卡",
                "primary_strategy": "连板接力",
                "index_strength": "strong",
                "emotion_strength": "strong",
            },
        ),
        _event(
            event_type="candidate_upsert",
            entity_type="candidate",
            entity_id=10,
            payload={
                "strategy": "first_to_second",
                "theme_id": 3,
                "score": 88,
                "rank": 1,
                "decision": "candidate",
            },
        ),
        _event(
            event_type="sector_stage_change",
            entity_type="theme",
            entity_id=3,
            payload={
                "from_stage": "fermentation",
                "to_stage": "climax",
                "strength_score": 80,
            },
        ),
    ]
    service.repo.list_runs.return_value = [_run()]
    service.repo.get_report.return_value = None
    service._load_stock_map = AsyncMock(  # type: ignore[method-assign]
        return_value={
            10: SimpleNamespace(
                id=10,
                code="000001",
                name="平安银行",
                rise_fall_pct=Decimal("2.5"),
            )
        }
    )
    service._load_theme_names = AsyncMock(  # type: ignore[method-assign]
        return_value={3: "人工智能"}
    )

    with patch(
        "app.services.review.ShortTermService.resolve_trade_date",
        side_effect=lambda d=None: d or date(2026, 7, 25),
    ):
        result = await service.get_day(day)

    assert result.degraded is False
    assert "review_events" not in result.missing_sources
    assert result.strategy_card is not None
    assert result.strategy_card["primary_strategy"] == "连板接力"
    assert len(result.candidates) == 1
    assert result.candidates[0].stock_code == "000001"
    assert result.candidates[0].theme_name == "人工智能"
    assert len(result.stage_transitions) == 1
    assert result.stage_transitions[0].to_stage == "climax"
    assert len(result.runs) == 1
    # 历史日不得用 live 填 same_day
    assert result.performance is not None
    assert result.performance.candidates[0].same_day_pct is None
    assert result.performance.candidates[0].reason == "无历史行情快照"


@pytest.mark.asyncio
async def test_day_review_degrades_to_snapshots_without_events():
    session = AsyncMock()
    service = ReviewService(session)
    service.repo = AsyncMock()
    day = date(2026, 7, 24)

    service.repo.list_events.return_value = []
    service.repo.list_runs.return_value = []
    service.repo.get_report.return_value = None

    snapshot = SimpleNamespace(
        theme_id=5,
        lifecycle_stage="climax",
        strength_score=70,
        mainline_score=60,
    )
    prior = SimpleNamespace(
        theme_id=5,
        lifecycle_stage="fermentation",
        strength_score=40,
        mainline_score=30,
    )
    candidate = SimpleNamespace(
        stock_id=20,
        theme_id=5,
        strategy="first_to_second",
        score=75,
        rank=1,
        decision="candidate",
    )
    service._load_sector_snapshots = AsyncMock(return_value=[snapshot])  # type: ignore[method-assign]
    service._load_sector_snapshots_for_date = AsyncMock(  # type: ignore[method-assign]
        side_effect=lambda d: [prior] if d == date(2026, 7, 23) else [snapshot]
    )
    service._load_legacy_candidates = AsyncMock(return_value=[candidate])  # type: ignore[method-assign]
    service._load_stock_map = AsyncMock(  # type: ignore[method-assign]
        return_value={
            20: SimpleNamespace(
                id=20, code="600000", name="浦发银行", rise_fall_pct=None
            )
        }
    )
    service._load_theme_names = AsyncMock(return_value={5: "机器人"})  # type: ignore[method-assign]

    with patch(
        "app.services.review.ShortTermService.resolve_trade_date",
        side_effect=lambda d=None: d or date(2026, 7, 25),
    ):
        result = await service.get_day(day)

    assert result.degraded is True
    assert "review_events" in result.missing_sources
    assert result.strategy_card is None
    assert len(result.candidates) == 1
    assert result.candidates[0].stock_name == "浦发银行"
    assert len(result.stage_transitions) == 1
    assert result.stage_transitions[0].from_stage == "fermentation"
    assert result.stage_transitions[0].to_stage == "climax"


@pytest.mark.asyncio
async def test_list_days_unions_runs_and_snapshots():
    session = AsyncMock()
    service = ReviewService(session)
    service.repo = AsyncMock()
    service.repo.list_trade_dates.return_value = [
        date(2026, 7, 22),
        date(2026, 7, 24),
    ]
    service._list_snapshot_trade_dates = AsyncMock(  # type: ignore[method-assign]
        return_value=[date(2026, 7, 23), date(2026, 7, 24)]
    )

    days = await service.list_days(date(2026, 7, 20), date(2026, 7, 25))

    assert days == [
        date(2026, 7, 22),
        date(2026, 7, 23),
        date(2026, 7, 24),
    ]


@pytest.mark.asyncio
async def test_theme_trajectory_from_snapshots():
    session = AsyncMock()
    service = ReviewService(session)
    service.repo = AsyncMock()
    service.repo.list_theme_events.return_value = []
    service.repo.list_runs.return_value = []
    service._load_theme_names = AsyncMock(return_value={9: "固态电池"})  # type: ignore[method-assign]
    service._load_lifecycle_history = AsyncMock(  # type: ignore[method-assign]
        return_value=[
            SimpleNamespace(
                trade_date=date(2026, 7, 22),
                lifecycle_stage="germination",
                strength_score=20,
            ),
            SimpleNamespace(
                trade_date=date(2026, 7, 23),
                lifecycle_stage="fermentation",
                strength_score=45,
            ),
            SimpleNamespace(
                trade_date=date(2026, 7, 24),
                lifecycle_stage="climax",
                strength_score=80,
            ),
        ]
    )
    service._load_theme_candidates = AsyncMock(return_value=[])  # type: ignore[method-assign]

    with patch(
        "app.services.review.ShortTermService.resolve_trade_date",
        return_value=date(2026, 7, 24),
    ):
        result = await service.get_theme(9, days=10)

    assert result.theme_id == 9
    assert result.theme_name == "固态电池"
    assert len(result.trajectory) == 3
    assert result.trajectory[-1].stage == "climax"
    assert result.trajectory[-1].strength_score == 80


@pytest.mark.asyncio
async def test_same_day_pct_only_for_resolved_today():
    session = AsyncMock()
    service = ReviewService(session)
    service.repo = AsyncMock()
    today = date(2026, 7, 24)

    service.repo.list_events.return_value = [
        _event(
            event_type="candidate_upsert",
            entity_type="candidate",
            entity_id=10,
            payload={
                "strategy": "first_to_second",
                "theme_id": None,
                "score": 50,
                "rank": 1,
                "decision": "candidate",
            },
        ),
    ]
    service.repo.list_runs.return_value = []
    service.repo.get_report.return_value = None
    service._load_stock_map = AsyncMock(  # type: ignore[method-assign]
        return_value={
            10: SimpleNamespace(
                id=10,
                code="000001",
                name="平安银行",
                rise_fall_pct=Decimal("3.2"),
            )
        }
    )
    service._load_theme_names = AsyncMock(return_value={})  # type: ignore[method-assign]

    with patch(
        "app.services.review.ShortTermService.resolve_trade_date",
        side_effect=lambda d=None: today if d is None else d,
    ):
        result = await service.get_day(today)

    assert result.performance is not None
    assert result.performance.candidates[0].same_day_pct == pytest.approx(3.2)
    assert result.performance.candidates[0].next_day_pct is None
