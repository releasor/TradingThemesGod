"""创建复盘台事件溯源三表：review_runs / review_events / review_ai_reports。"""

import sqlalchemy as sa
from alembic import op

revision = "016_create_review_desk_tables"
down_revision = "015_create_short_term_radar_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "review_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("run_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("source_status", sa.JSON(), nullable=False),
        sa.Column("request_meta", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="复盘运行记录",
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index(
        "idx_review_runs_date_started",
        "review_runs",
        ["trade_date", "started_at"],
    )
    op.create_index(
        "idx_review_runs_type_date",
        "review_runs",
        ["run_type", "trade_date"],
    )

    op.create_table(
        "review_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=True),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.BigInteger(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["run_id"], ["review_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        comment="复盘实体事件",
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index(
        "idx_review_events_date_type",
        "review_events",
        ["trade_date", "event_type"],
    )
    op.create_index(
        "idx_review_events_run",
        "review_events",
        ["run_id"],
    )
    op.create_index(
        "idx_review_events_entity",
        "review_events",
        ["entity_type", "entity_id", "trade_date"],
    )

    op.create_table(
        "review_ai_reports",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("content_md", sa.Text(), nullable=False),
        sa.Column("content_json", sa.JSON(), nullable=False),
        sa.Column("model_name", sa.String(length=200), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("source_run_ids", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "trade_date",
            "user_id",
            name="uq_review_ai_reports_date_user",
        ),
        comment="复盘 AI 题材日报",
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index(
        "ix_review_ai_reports_trade_date",
        "review_ai_reports",
        ["trade_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_review_ai_reports_trade_date", table_name="review_ai_reports")
    op.drop_table("review_ai_reports")

    op.drop_index("idx_review_events_entity", table_name="review_events")
    op.drop_index("idx_review_events_run", table_name="review_events")
    op.drop_index("idx_review_events_date_type", table_name="review_events")
    op.drop_table("review_events")

    op.drop_index("idx_review_runs_type_date", table_name="review_runs")
    op.drop_index("idx_review_runs_date_started", table_name="review_runs")
    op.drop_table("review_runs")
