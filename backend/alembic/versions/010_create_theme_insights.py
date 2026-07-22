"""创建题材档案、驱动事件和每日市场快照。"""

import sqlalchemy as sa

from alembic import op

revision = "010_create_theme_insights"
down_revision = "009_create_model_providers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "theme_profiles",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("theme_id", sa.BigInteger(), nullable=False),
        sa.Column("definition", sa.Text(), nullable=False),
        sa.Column("core_logic", sa.Text(), nullable=False),
        sa.Column("applications", sa.JSON(), nullable=False),
        sa.Column("catalysts", sa.JSON(), nullable=False),
        sa.Column("risks", sa.JSON(), nullable=False),
        sa.Column("sources", sa.JSON(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["theme_id"], ["themes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("theme_id", name="idx_theme_profiles_theme_id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )

    op.create_table(
        "theme_driver_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("theme_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("url_hash", sa.String(length=64), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("relevance_score", sa.Integer(), nullable=False),
        sa.Column("crawled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["theme_id"], ["themes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index(
        "idx_theme_driver_events_theme_url",
        "theme_driver_events",
        ["theme_id", "url_hash"],
        unique=True,
    )
    op.create_index(
        "idx_theme_driver_events_theme_id",
        "theme_driver_events",
        ["theme_id"],
    )
    op.create_index(
        "idx_theme_driver_events_published_at",
        "theme_driver_events",
        ["published_at"],
    )
    op.create_index(
        "idx_theme_driver_events_theme_published",
        "theme_driver_events",
        ["theme_id", "published_at"],
    )

    op.create_table(
        "theme_market_snapshots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("theme_id", sa.BigInteger(), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("up_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("down_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("flat_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("suspended_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("limit_up_count", sa.Integer(), nullable=True),
        sa.Column("limit_down_count", sa.Integer(), nullable=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["theme_id"], ["themes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index(
        "idx_theme_market_snapshots_theme_date",
        "theme_market_snapshots",
        ["theme_id", "trade_date"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("theme_market_snapshots")
    op.drop_table("theme_driver_events")
    op.drop_table("theme_profiles")
