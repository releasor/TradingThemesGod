"""复盘台 ORM 模型测试。"""

from app.models.review import ReviewRun, ReviewEvent, ReviewAiReport


def test_review_run_columns_and_indexes():
    cols = {c.name for c in ReviewRun.__table__.columns}
    assert {"trade_date", "run_type", "status", "source_status", "request_meta", "started_at", "finished_at"} <= cols
    names = {i.name for i in ReviewRun.__table__.indexes}
    assert "idx_review_runs_date_started" in names


def test_review_event_columns_and_indexes():
    cols = {c.name for c in ReviewEvent.__table__.columns}
    assert {"run_id", "trade_date", "event_type", "entity_type", "entity_id", "payload_json", "occurred_at"} <= cols
    names = {i.name for i in ReviewEvent.__table__.indexes}
    assert "idx_review_events_date_type" in names
    assert "idx_review_events_entity" in names


def test_review_ai_report_unique():
    names = {c.name for c in ReviewAiReport.__table__.constraints if hasattr(c, "name") and c.name}
    # UniqueConstraint name
    assert "uq_review_ai_reports_date_user" in {
        u.name for u in ReviewAiReport.__table__.constraints if u.name
    }
