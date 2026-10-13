"""创建个人 AI OS 相关表。"""

import sqlalchemy as sa
from alembic import op

revision = "024_create_personal_os_tables"
down_revision = "023_create_prompt_workbench_tables"
branch_labels = None
depends_on = None

_TS = dict(
    server_default=sa.text("CURRENT_TIMESTAMP"),
    nullable=False,
)


def upgrade() -> None:
    op.create_table(
        "os_profiles",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=True),
        sa.Column("goals", sa.Text(), nullable=True),
        sa.Column("health_baseline", sa.JSON(), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("memory_policy", sa.JSON(), nullable=False),
        sa.Column("module_flags", sa.JSON(), nullable=False),
        sa.Column("model_prefs", sa.JSON(), nullable=False),
        sa.Column("report_prompt_appendix", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), **_TS),
        sa.Column("updated_at", sa.DateTime(timezone=True), **_TS),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("ix_os_profiles_user_id", "os_profiles", ["user_id"])

    op.create_table(
        "os_notes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), **_TS),
        sa.Column("updated_at", sa.DateTime(timezone=True), **_TS),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("ix_os_notes_user_id", "os_notes", ["user_id"])

    op.create_table(
        "os_chat_sessions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("provider_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), **_TS),
        sa.Column("updated_at", sa.DateTime(timezone=True), **_TS),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("ix_os_chat_sessions_user_id", "os_chat_sessions", ["user_id"])

    op.create_table(
        "os_chat_messages",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("provider_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), **_TS),
        sa.ForeignKeyConstraint(
            ["session_id"], ["os_chat_sessions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index(
        "ix_os_chat_messages_session_id", "os_chat_messages", ["session_id"]
    )

    op.create_table(
        "os_journal_entries",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("media_refs", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), **_TS),
        sa.Column("updated_at", sa.DateTime(timezone=True), **_TS),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("ix_os_journal_entries_user_id", "os_journal_entries", ["user_id"])
    op.create_index("ix_os_journal_entries_kind", "os_journal_entries", ["kind"])

    op.create_table(
        "os_daily_reports",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("provider_id", sa.BigInteger(), nullable=True),
        sa.Column("entry_ids", sa.JSON(), nullable=False),
        sa.Column("feedback_score", sa.Integer(), nullable=True),
        sa.Column("feedback_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), **_TS),
        sa.Column("updated_at", sa.DateTime(timezone=True), **_TS),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "report_date", name="uq_os_daily_reports_user_date"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("ix_os_daily_reports_user_id", "os_daily_reports", ["user_id"])

    op.create_table(
        "os_decision_threads",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("constraints", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="open"),
        sa.Column("chosen_option_id", sa.BigInteger(), nullable=True),
        sa.Column("outcome_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), **_TS),
        sa.Column("updated_at", sa.DateTime(timezone=True), **_TS),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index(
        "ix_os_decision_threads_user_id", "os_decision_threads", ["user_id"]
    )

    op.create_table(
        "os_decision_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("thread_id", sa.BigInteger(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("provider_ids", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), **_TS),
        sa.Column("updated_at", sa.DateTime(timezone=True), **_TS),
        sa.ForeignKeyConstraint(
            ["thread_id"], ["os_decision_threads.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("ix_os_decision_runs_thread_id", "os_decision_runs", ["thread_id"])

    op.create_table(
        "os_decision_options",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("tier", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("provider_id", sa.BigInteger(), nullable=True),
        sa.Column("raw_reply", sa.Text(), nullable=True),
        sa.Column("selected", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("feedback_score", sa.Float(), nullable=True),
        sa.Column("feedback_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), **_TS),
        sa.ForeignKeyConstraint(
            ["run_id"], ["os_decision_runs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index(
        "ix_os_decision_options_run_id", "os_decision_options", ["run_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_os_decision_options_run_id", table_name="os_decision_options")
    op.drop_table("os_decision_options")
    op.drop_index("ix_os_decision_runs_thread_id", table_name="os_decision_runs")
    op.drop_table("os_decision_runs")
    op.drop_index("ix_os_decision_threads_user_id", table_name="os_decision_threads")
    op.drop_table("os_decision_threads")
    op.drop_index("ix_os_daily_reports_user_id", table_name="os_daily_reports")
    op.drop_table("os_daily_reports")
    op.drop_index("ix_os_journal_entries_kind", table_name="os_journal_entries")
    op.drop_index("ix_os_journal_entries_user_id", table_name="os_journal_entries")
    op.drop_table("os_journal_entries")
    op.drop_index("ix_os_chat_messages_session_id", table_name="os_chat_messages")
    op.drop_table("os_chat_messages")
    op.drop_index("ix_os_chat_sessions_user_id", table_name="os_chat_sessions")
    op.drop_table("os_chat_sessions")
    op.drop_index("ix_os_notes_user_id", table_name="os_notes")
    op.drop_table("os_notes")
    op.drop_index("ix_os_profiles_user_id", table_name="os_profiles")
    op.drop_table("os_profiles")
