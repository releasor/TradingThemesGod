"""催化雷达 ORM 模型测试。"""

from app.models.catalyst import CatalystClassification
from app.models.theme_driver_event import ThemeDriverEvent


def test_driver_event_has_classification_columns():
    cols = {c.name for c in ThemeDriverEvent.__table__.columns}
    assert {"freshness", "actor_type", "classified_by", "classified_at"} <= cols


def test_catalyst_classification_indexes():
    names = {i.name for i in CatalystClassification.__table__.indexes}
    assert "idx_catalyst_classifications_event_created" in names
