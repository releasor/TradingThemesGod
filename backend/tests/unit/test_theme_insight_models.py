"""题材洞察持久化模型和迁移元数据测试。"""

import importlib.util
from pathlib import Path

from app.models.theme import Theme
from app.models.theme_driver_event import ThemeDriverEvent
from app.models.theme_market_snapshot import ThemeMarketSnapshot
from app.models.theme_profile import ThemeProfile


def test_theme_profile_has_one_to_one_theme_constraint():
    assert ThemeProfile.__tablename__ == "theme_profiles"
    assert ThemeProfile.__table__.c.theme_id.unique is True


def test_driver_event_has_theme_url_unique_index():
    indexes = {index.name: index for index in ThemeDriverEvent.__table__.indexes}
    index = indexes["idx_theme_driver_events_theme_url"]

    assert index.unique is True
    assert [column.name for column in index.columns] == ["theme_id", "url_hash"]


def test_driver_event_has_cross_refresh_event_key_index():
    indexes = {index.name: index for index in ThemeDriverEvent.__table__.indexes}
    index = indexes["idx_theme_driver_events_theme_event"]

    assert ThemeDriverEvent.__table__.c.event_key.nullable is True
    assert index.unique is True
    assert [column.name for column in index.columns] == ["theme_id", "event_key"]


def test_driver_event_has_published_at_lookup_index():
    indexes = {index.name: index for index in ThemeDriverEvent.__table__.indexes}
    index = indexes["idx_theme_driver_events_published_at"]

    assert index.unique is False
    assert [column.name for column in index.columns] == ["published_at"]


def test_driver_event_has_theme_id_lookup_index():
    indexes = {index.name: index for index in ThemeDriverEvent.__table__.indexes}
    index = indexes["idx_theme_driver_events_theme_id"]

    assert index.unique is False
    assert [column.name for column in index.columns] == ["theme_id"]


def test_market_snapshot_distinguishes_zero_from_unavailable_limit_pool():
    assert ThemeMarketSnapshot.__table__.c.limit_up_count.nullable is True
    assert ThemeMarketSnapshot.__table__.c.limit_down_count.nullable is True


def test_theme_has_persistent_insight_refresh_cursor():
    indexes = {index.name: index for index in Theme.__table__.indexes}

    assert Theme.__table__.c.insights_last_attempted_at.nullable is True
    assert "idx_themes_insights_last_attempted_at" in indexes


def _load_migration():
    path = (
        Path(__file__).parents[2]
        / "alembic"
        / "versions"
        / "010_create_theme_insights.py"
    )
    spec = importlib.util.spec_from_file_location("migration_010_theme_insights", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_refresh_key_migration():
    path = (
        Path(__file__).parents[2]
        / "alembic"
        / "versions"
        / "011_add_theme_insight_refresh_keys.py"
    )
    spec = importlib.util.spec_from_file_location("migration_011_refresh_keys", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_upgrade_declares_tables_indexes_and_foreign_keys(monkeypatch):
    migration = _load_migration()
    tables: dict[str, tuple] = {}
    indexes: dict[str, tuple[str, tuple[str, ...], bool]] = {}

    monkeypatch.setattr(
        migration.op,
        "create_table",
        lambda name, *items, **_kwargs: tables.setdefault(name, items),
    )
    monkeypatch.setattr(
        migration.op,
        "create_index",
        lambda name, table, columns, unique=False: indexes.setdefault(
            name, (table, tuple(columns), unique)
        ),
    )

    migration.upgrade()

    assert set(tables) == {
        "theme_profiles",
        "theme_driver_events",
        "theme_market_snapshots",
    }
    assert indexes["idx_theme_driver_events_theme_url"] == (
        "theme_driver_events",
        ("theme_id", "url_hash"),
        True,
    )
    assert indexes["idx_theme_driver_events_published_at"] == (
        "theme_driver_events",
        ("published_at",),
        False,
    )
    assert indexes["idx_theme_driver_events_theme_id"] == (
        "theme_driver_events",
        ("theme_id",),
        False,
    )
    for items in tables.values():
        foreign_keys = [
            item for item in items if item.__class__.__name__ == "ForeignKeyConstraint"
        ]
        assert len(foreign_keys) == 1
        assert foreign_keys[0].ondelete == "CASCADE"


def test_migration_downgrade_drops_dependent_tables_first(monkeypatch):
    migration = _load_migration()
    dropped: list[str] = []
    monkeypatch.setattr(migration.op, "drop_table", dropped.append)

    migration.downgrade()

    assert dropped == [
        "theme_market_snapshots",
        "theme_driver_events",
        "theme_profiles",
    ]


def test_refresh_key_migration_adds_event_key_and_persistent_cursor(monkeypatch):
    migration = _load_refresh_key_migration()
    assert len(migration.revision) <= 32
    columns: list[tuple[str, str]] = []
    indexes: list[tuple[str, str, tuple[str, ...], bool]] = []
    monkeypatch.setattr(
        migration.op,
        "add_column",
        lambda table, column: columns.append((table, column.name)),
    )
    monkeypatch.setattr(
        migration.op,
        "create_index",
        lambda name, table, fields, unique=False: indexes.append(
            (name, table, tuple(fields), unique)
        ),
    )

    migration.upgrade()

    assert migration.down_revision == "010_create_theme_insights"
    assert columns == [
        ("theme_driver_events", "event_key"),
        ("themes", "insights_last_attempted_at"),
    ]
    assert (
        "idx_theme_driver_events_theme_event",
        "theme_driver_events",
        ("theme_id", "event_key"),
        True,
    ) in indexes
