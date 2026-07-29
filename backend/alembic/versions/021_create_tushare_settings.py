"""创建 tushare_settings 单例表。"""

import sqlalchemy as sa
from alembic import op

revision = "021_create_tushare_settings"
down_revision = "020_create_trading_calendar_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tushare_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("token_encrypted", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        comment="Tushare全局配置",
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.execute(
        "INSERT INTO tushare_settings (id, enabled) VALUES (1, 0)"
    )


def downgrade() -> None:
    op.drop_table("tushare_settings")
