"""题材市场快照增加涨跌幅字段，供周期指数强度计算。"""

import sqlalchemy as sa

from alembic import op

revision = "013_add_snapshot_rise_fall_pct"
down_revision = "012_user_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "theme_market_snapshots",
        sa.Column(
            "rise_fall_pct",
            sa.Numeric(10, 2),
            nullable=True,
            comment="板块涨跌幅(%)",
        ),
    )


def downgrade() -> None:
    op.drop_column("theme_market_snapshots", "rise_fall_pct")
