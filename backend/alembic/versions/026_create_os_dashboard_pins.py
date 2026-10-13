"""创建个人 AI OS 仪表盘钉选表。"""

import sqlalchemy as sa
from alembic import op

revision = "026_create_os_dashboard_pins"
down_revision = "025_add_os_decision_prompt_appendix"
branch_labels = None
depends_on = None

_TS = dict(
    server_default=sa.text("CURRENT_TIMESTAMP"),
    nullable=False,
)


def upgrade() -> None:
    op.create_table(
        "os_dashboard_pins",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), **_TS),
        sa.Column("updated_at", sa.DateTime(timezone=True), **_TS),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "source_type",
            "source_id",
            name="uq_os_dashboard_pins_user_source",
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("ix_os_dashboard_pins_user_id", "os_dashboard_pins", ["user_id"])
    op.create_index(
        "ix_os_dashboard_pins_user_type",
        "os_dashboard_pins",
        ["user_id", "source_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_os_dashboard_pins_user_type", table_name="os_dashboard_pins")
    op.drop_index("ix_os_dashboard_pins_user_id", table_name="os_dashboard_pins")
    op.drop_table("os_dashboard_pins")
