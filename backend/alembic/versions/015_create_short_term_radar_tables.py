"""创建 short-term radar tables including lifecycle strength fields."""

import sqlalchemy as sa
from alembic import op

revision = "015_create_short_term_radar_tables"
down_revision = "014_create_stock_ai_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Default alembic_version.version_num is VARCHAR(32); this revision id is longer.
    op.execute("ALTER TABLE alembic_version MODIFY version_num VARCHAR(64) NOT NULL")

    op.create_table(
        "daily_stock_signals",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("stock_id", sa.BigInteger(), nullable=False),
        sa.Column("theme_id", sa.BigInteger(), nullable=True),
        sa.Column("signal_type", sa.String(length=32), nullable=False),
        sa.Column("limit_up_order", sa.Integer(), nullable=True),
        sa.Column("first_limit_up_at", sa.Time(), nullable=True),
        sa.Column("last_limit_up_at", sa.Time(), nullable=True),
        sa.Column("open_board_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("streak_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_one_word", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_failed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("price", sa.Numeric(12, 4), nullable=True),
        sa.Column("turnover_rate", sa.Numeric(10, 4), nullable=True),
        sa.Column("amount", sa.Numeric(20, 4), nullable=True),
        sa.Column("market_cap", sa.Numeric(20, 4), nullable=True),
        sa.Column("float_market_cap", sa.Numeric(20, 4), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("source_payload", sa.JSON(), nullable=True),
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
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["theme_id"], ["themes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "trade_date",
            "stock_id",
            "signal_type",
            name="uq_daily_stock_signals_date_stock_type",
        ),
        comment="每日个股短线信号",
    )
    op.create_index(
        "idx_daily_stock_signals_date_type",
        "daily_stock_signals",
        ["trade_date", "signal_type"],
    )
    op.create_index(
        "idx_daily_stock_signals_date_stock",
        "daily_stock_signals",
        ["trade_date", "stock_id"],
    )
    op.create_index(
        "idx_daily_stock_signals_date_theme",
        "daily_stock_signals",
        ["trade_date", "theme_id"],
    )

    op.create_table(
        "dragon_tiger_entries",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("stock_id", sa.BigInteger(), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("buy_amount", sa.Numeric(20, 4), nullable=True),
        sa.Column("sell_amount", sa.Numeric(20, 4), nullable=True),
        sa.Column("net_amount", sa.Numeric(20, 4), nullable=True),
        sa.Column("seat_summary", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("source_payload", sa.JSON(), nullable=True),
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
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "trade_date",
            "stock_id",
            "reason",
            name="uq_dragon_tiger_entries_date_stock_reason",
        ),
        comment="龙虎榜明细",
    )
    op.create_index(
        "idx_dragon_tiger_entries_date_stock",
        "dragon_tiger_entries",
        ["trade_date", "stock_id"],
    )
    op.create_index(
        "idx_dragon_tiger_entries_date_net",
        "dragon_tiger_entries",
        ["trade_date", "net_amount"],
    )

    op.create_table(
        "sector_rotation_snapshots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("theme_id", sa.BigInteger(), nullable=False),
        sa.Column("trend_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("emotion_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rotation_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mainline_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("risk_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("strong_stock_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("limit_up_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_limit_up_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("near_limit_up_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latest_catalyst_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False, server_default="rules"),
        sa.Column("lifecycle_stage", sa.String(length=32), nullable=False),
        sa.Column("lifecycle_confidence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("strength_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("limit_quality_score", sa.Integer(), nullable=True),
        sa.Column("flow_score", sa.Integer(), nullable=True),
        sa.Column("leader_clarity_score", sa.Integer(), nullable=True),
        sa.Column("breadth_score", sa.Integer(), nullable=True),
        sa.Column("score_breakdown", sa.JSON(), nullable=False),
        sa.Column("degraded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("missing_metrics", sa.JSON(), nullable=False),
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
        sa.ForeignKeyConstraint(["theme_id"], ["themes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "trade_date",
            "theme_id",
            name="uq_sector_rotation_snapshots_date_theme",
        ),
        comment="题材日轮动与生命周期快照",
    )
    op.create_index(
        "idx_sector_rotation_snapshots_date_theme",
        "sector_rotation_snapshots",
        ["trade_date", "theme_id"],
    )
    op.create_index(
        "idx_sector_rotation_snapshots_date_mainline",
        "sector_rotation_snapshots",
        ["trade_date", "mainline_score"],
    )

    op.create_table(
        "short_term_signal_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_status", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
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
        comment="短线信号刷新运行记录",
    )
    op.create_index(
        "idx_short_term_signal_runs_date_status",
        "short_term_signal_runs",
        ["trade_date", "status"],
    )

    op.create_table(
        "short_term_candidates",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("strategy", sa.String(length=64), nullable=False),
        sa.Column("stock_id", sa.BigInteger(), nullable=False),
        sa.Column("theme_id", sa.BigInteger(), nullable=True),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rank", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("matched_rules", sa.JSON(), nullable=False),
        sa.Column("excluded_rules", sa.JSON(), nullable=False),
        sa.Column("risk_flags", sa.JSON(), nullable=False),
        sa.Column("outlook", sa.Text(), nullable=False),
        sa.Column("operation_advice", sa.Text(), nullable=False),
        sa.Column("tracking_focus", sa.Text(), nullable=False),
        sa.Column("core_conclusion", sa.Text(), nullable=False),
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
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["theme_id"], ["themes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "trade_date",
            "strategy",
            "stock_id",
            name="uq_short_term_candidates_date_strategy_stock",
        ),
        comment="短线规则候选结果",
    )
    op.create_index(
        "idx_short_term_candidates_date_strategy_rank",
        "short_term_candidates",
        ["trade_date", "strategy", "rank"],
    )
    op.create_index(
        "idx_short_term_candidates_date_stock",
        "short_term_candidates",
        ["trade_date", "stock_id"],
    )
    op.create_index(
        "idx_short_term_candidates_date_theme",
        "short_term_candidates",
        ["trade_date", "theme_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_short_term_candidates_date_theme", table_name="short_term_candidates"
    )
    op.drop_index(
        "idx_short_term_candidates_date_stock", table_name="short_term_candidates"
    )
    op.drop_index(
        "idx_short_term_candidates_date_strategy_rank",
        table_name="short_term_candidates",
    )
    op.drop_table("short_term_candidates")

    op.drop_index(
        "idx_short_term_signal_runs_date_status",
        table_name="short_term_signal_runs",
    )
    op.drop_table("short_term_signal_runs")

    op.drop_index(
        "idx_sector_rotation_snapshots_date_mainline",
        table_name="sector_rotation_snapshots",
    )
    op.drop_index(
        "idx_sector_rotation_snapshots_date_theme",
        table_name="sector_rotation_snapshots",
    )
    op.drop_table("sector_rotation_snapshots")

    op.drop_index(
        "idx_dragon_tiger_entries_date_net", table_name="dragon_tiger_entries"
    )
    op.drop_index(
        "idx_dragon_tiger_entries_date_stock", table_name="dragon_tiger_entries"
    )
    op.drop_table("dragon_tiger_entries")

    op.drop_index(
        "idx_daily_stock_signals_date_theme", table_name="daily_stock_signals"
    )
    op.drop_index(
        "idx_daily_stock_signals_date_stock", table_name="daily_stock_signals"
    )
    op.drop_index(
        "idx_daily_stock_signals_date_type", table_name="daily_stock_signals"
    )
    op.drop_table("daily_stock_signals")
