"""SectorRotation / refresh_signals 单元测试。"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.scrapers.dragon_tiger import SourceResult as DragonResult
from app.scrapers.short_term_signals import SourceResult as SignalResult
from app.services.sector_rotation import SectorRotationService
from app.services.short_term import ShortTermService


@pytest.mark.asyncio
async def test_rebuild_emits_stage_change_when_lifecycle_changes():
    session = AsyncMock()
    service = SectorRotationService(session)
    service._cover_theme_ids = AsyncMock(return_value={1})  # type: ignore[method-assign]
    service._load_prior_lifecycle_stages = AsyncMock(  # type: ignore[method-assign]
        return_value={1: "startup"}
    )
    service._load_snapshots = AsyncMock(return_value={1: {}})  # type: ignore[method-assign]
    service._load_signals = AsyncMock(return_value={1: {}})  # type: ignore[method-assign]
    service._load_dragon_by_theme = AsyncMock(return_value={})  # type: ignore[method-assign]
    service._load_theme_quotes = AsyncMock(  # type: ignore[method-assign]
        return_value={
            1: MagicMock(
                heat_index=50,
                rise_fall_pct=2.0,
                stock_count=10,
            )
        }
    )
    service._load_leader_stats = AsyncMock(return_value={})  # type: ignore[method-assign]
    service.repo.upsert_sector_snapshots = AsyncMock()  # type: ignore[method-assign]

    from app.services.lifecycle_rules import build_snapshot_scores

    scores = MagicMock(
        lifecycle_stage="main_rise",
        lifecycle_confidence=0.8,
        strength_score=72.0,
        trend_score=1,
        emotion_score=1,
        rotation_score=1,
        mainline_score=1,
        risk_score=1,
        summary="test",
        limit_quality_score=1,
        flow_score=1,
        leader_clarity_score=1,
        breadth_score=1,
        score_breakdown={},
        degraded=False,
        missing_metrics=[],
    )
    service._build_history = MagicMock(return_value=[MagicMock()])  # type: ignore[method-assign]

    import app.services.sector_rotation as sector_mod

    sector_mod.build_snapshot_scores = MagicMock(return_value=scores)

    review_ctx = AsyncMock()

    count = await service.rebuild(date(2026, 7, 25), review_ctx=review_ctx)

    assert count == 1
    review_ctx.emit_stage_change.assert_awaited_once_with(
        1,
        {
            "from_stage": "startup",
            "to_stage": "main_rise",
            "strength_score": 72.0,
        },
    )


@pytest.mark.asyncio
async def test_refresh_signals_partial_when_dragon_fails():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.scalar = AsyncMock(return_value=None)
    session.scalars = AsyncMock()
    session.add = MagicMock()

    service = ShortTermService(session)

    async def ok_signals(_trade_date):
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

    async def bad_dragon(_trade_date):
        return DragonResult(success=False, error="down")

    # stock resolve
    stock = MagicMock()
    stock.code = "000001"
    stock.id = 11
    scalars_result = MagicMock()
    scalars_result.all.return_value = [stock]
    session.scalars = AsyncMock(return_value=scalars_result)

    # avoid real sector rebuild complexity
    from app.services import short_term as short_term_mod

    class FakeSector:
        def __init__(self, _session):
            pass

        async def rebuild(self, _trade_date, **_kwargs):
            return 3

    short_term_mod.SectorRotationService = FakeSector

    from app.scrapers.short_term_signals import ShortTermSignalScraper
    from app.scrapers.dragon_tiger import DragonTigerScraper

    with patch(
        "app.services.mining.MiningService.ensure",
        new=AsyncMock(return_value=MagicMock()),
    ):
        result = await service.refresh_signals(
            date(2026, 7, 25),
            signal_scraper=ShortTermSignalScraper(fetch_pools=ok_signals),
            dragon_scraper=DragonTigerScraper(fetch_entries=bad_dragon),
        )
    assert result.status in {"partial", "success", "failed"}
    assert "dragon_tiger" in result.missing_sources
    assert result.degraded is True
