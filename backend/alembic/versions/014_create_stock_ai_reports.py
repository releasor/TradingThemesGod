"""创建 stock_ai_reports 表：按用户+股票缓存最近一份 AI 研判。"""

import sqlalchemy as sa

from alembic import op

revision = "014_create_stock_ai_reports"
down_revision = "013_add_snapshot_rise_fall_pct"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stock_ai_reports",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("stock_code", sa.String(length=6), nullable=False),
        sa.Column("stock_name", sa.String(length=100), nullable=True),
        sa.Column("verdict", sa.String(length=16), nullable=False),
        sa.Column("horizon_short", sa.Text(), nullable=False),
        sa.Column("horizon_swing", sa.Text(), nullable=False),
        sa.Column("horizon_medium_long", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("sections", sa.JSON(), nullable=False),
        sa.Column("full_report", sa.Text(), nullable=False),
        sa.Column("context_digest", sa.JSON(), nullable=False),
        sa.Column("model_provider_id", sa.BigInteger(), nullable=True),
        sa.Column("model_name", sa.String(length=200), nullable=True),
        sa.Column("elapsed_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.UniqueConstraint("user_id", "stock_code", name="uq_stock_ai_reports_user_code"),
    )
    op.create_index("ix_stock_ai_reports_user_id", "stock_ai_reports", ["user_id"])
    op.create_index("ix_stock_ai_reports_stock_code", "stock_ai_reports", ["stock_code"])
    op.create_index(
        "ix_stock_ai_reports_generated_at", "stock_ai_reports", ["generated_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_stock_ai_reports_generated_at", table_name="stock_ai_reports")
    op.drop_index("ix_stock_ai_reports_stock_code", table_name="stock_ai_reports")
    op.drop_index("ix_stock_ai_reports_user_id", table_name="stock_ai_reports")
    op.drop_table("stock_ai_reports")
