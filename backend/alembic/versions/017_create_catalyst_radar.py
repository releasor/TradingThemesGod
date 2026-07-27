"""催化雷达：扩展 theme_driver_events 分类列并创建 catalyst_classifications 表。"""

import sqlalchemy as sa
from alembic import op

revision = "017_create_catalyst_radar"
down_revision = "016_create_review_desk_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "theme_driver_events",
        sa.Column(
            "freshness",
            sa.String(length=16),
            nullable=False,
            server_default="unknown",
        ),
    )
    op.add_column(
        "theme_driver_events",
        sa.Column(
            "actor_type",
            sa.String(length=16),
            nullable=False,
            server_default="unknown",
        ),
    )
    op.add_column(
        "theme_driver_events",
        sa.Column("classified_by", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "theme_driver_events",
        sa.Column("classified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_theme_driver_events_freshness_published",
        "theme_driver_events",
        ["freshness", "published_at"],
    )
    op.create_index(
        "idx_theme_driver_events_actor_published",
        "theme_driver_events",
        ["actor_type", "published_at"],
    )

    op.create_table(
        "catalyst_classifications",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("freshness", sa.String(length=16), nullable=False),
        sa.Column("actor_type", sa.String(length=16), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=False),
        sa.Column("model_name", sa.String(length=200), nullable=True),
        sa.Column("confidence", sa.Integer(), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["theme_driver_events.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="催化分类审计快照",
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index(
        "idx_catalyst_classifications_event_created",
        "catalyst_classifications",
        ["event_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_catalyst_classifications_event_created",
        table_name="catalyst_classifications",
    )
    op.drop_table("catalyst_classifications")

    op.drop_index(
        "idx_theme_driver_events_actor_published",
        table_name="theme_driver_events",
    )
    op.drop_index(
        "idx_theme_driver_events_freshness_published",
        table_name="theme_driver_events",
    )
    op.drop_column("theme_driver_events", "classified_at")
    op.drop_column("theme_driver_events", "classified_by")
    op.drop_column("theme_driver_events", "actor_type")
    op.drop_column("theme_driver_events", "freshness")
