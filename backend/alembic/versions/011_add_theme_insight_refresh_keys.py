"""增加题材洞察跨批次去重键和持久刷新游标。

Revision ID: 011_theme_insight_keys
Revises: 010_create_theme_insights
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "011_theme_insight_keys"
down_revision: str | None = "010_create_theme_insights"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "theme_driver_events",
        sa.Column("event_key", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "idx_theme_driver_events_theme_event",
        "theme_driver_events",
        ["theme_id", "event_key"],
        unique=True,
    )
    op.add_column(
        "themes",
        sa.Column(
            "insights_last_attempted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_index(
        "idx_themes_insights_last_attempted_at",
        "themes",
        ["insights_last_attempted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_themes_insights_last_attempted_at", table_name="themes")
    op.drop_column("themes", "insights_last_attempted_at")
    op.drop_index(
        "idx_theme_driver_events_theme_event",
        table_name="theme_driver_events",
    )
    op.drop_column("theme_driver_events", "event_key")
