"""创建 trading_calendar_days / trading_calendar_meta。"""

import sqlalchemy as sa
from alembic import op

revision = "020_create_trading_calendar_tables"
down_revision = "019_create_mainline_graph_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trading_calendar_days",
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("trade_date"),
        comment="A股开市日",
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_table(
        "trading_calendar_meta",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("min_date", sa.Date(), nullable=True),
        sa.Column("max_date", sa.Date(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="交易日历同步元信息",
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.execute(
        "INSERT INTO trading_calendar_meta (id, source, row_count) VALUES (1, 'akshare_sina', 0)"
    )


def downgrade() -> None:
    op.drop_table("trading_calendar_meta")
    op.drop_table("trading_calendar_days")
