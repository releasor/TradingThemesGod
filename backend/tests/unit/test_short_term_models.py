"""短线雷达 ORM 模型测试。"""

from app.models.short_term_signal import (
    DailyStockSignal,
    DragonTigerEntry,
    SectorRotationSnapshot,
    ShortTermCandidate,
    ShortTermSignalRun,
)


def test_short_term_models_define_expected_tables_and_indexes():
    assert DailyStockSignal.__tablename__ == "daily_stock_signals"
    assert DragonTigerEntry.__tablename__ == "dragon_tiger_entries"
    assert SectorRotationSnapshot.__tablename__ == "sector_rotation_snapshots"
    assert ShortTermSignalRun.__tablename__ == "short_term_signal_runs"
    assert ShortTermCandidate.__tablename__ == "short_term_candidates"

    daily_indexes = {index.name for index in DailyStockSignal.__table__.indexes}
    assert "idx_daily_stock_signals_date_type" in daily_indexes
    assert "idx_daily_stock_signals_date_stock" in daily_indexes
    assert "idx_daily_stock_signals_date_theme" in daily_indexes

    candidate_indexes = {index.name for index in ShortTermCandidate.__table__.indexes}
    assert "idx_short_term_candidates_date_strategy_rank" in candidate_indexes


def test_sector_rotation_has_lifecycle_columns():
    cols = {c.name for c in SectorRotationSnapshot.__table__.columns}
    assert "lifecycle_stage" in cols
    assert "strength_score" in cols
    assert "limit_quality_score" in cols
    assert "flow_score" in cols
    assert "leader_clarity_score" in cols
    assert "breadth_score" in cols
    assert "score_breakdown" in cols
    assert "degraded" in cols
    assert "missing_metrics" in cols
