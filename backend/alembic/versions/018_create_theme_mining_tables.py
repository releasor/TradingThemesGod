"""创建题材挖掘三表：theme_mining_cards / theme_mining_members / theme_mining_notes。"""

import sqlalchemy as sa
from alembic import op

revision = "018_create_theme_mining_tables"
down_revision = "017_create_catalyst_radar"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "theme_mining_cards",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("theme_id", sa.BigInteger(), nullable=False),
        sa.Column("mining_type", sa.String(length=32), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("lifecycle_stage", sa.String(length=32), nullable=False),
        sa.Column("strength_score", sa.Integer(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("score_breakdown", sa.JSON(), nullable=False),
        sa.Column("degraded", sa.Boolean(), nullable=False),
        sa.Column("missing_metrics", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["theme_id"], ["themes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "trade_date",
            "theme_id",
            "mining_type",
            name="uq_theme_mining_cards_date_theme_type",
        ),
        comment="题材挖掘日快照卡",
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index(
        "idx_theme_mining_cards_date_type_rank",
        "theme_mining_cards",
        ["trade_date", "mining_type", "rank"],
    )

    op.create_table(
        "theme_mining_members",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("card_id", sa.BigInteger(), nullable=False),
        sa.Column("stock_id", sa.BigInteger(), nullable=False),
        sa.Column("concept_node_id", sa.BigInteger(), nullable=True),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("role_tag", sa.String(length=32), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["card_id"],
            ["theme_mining_cards.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["concept_node_id"],
            ["concept_nodes.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "card_id",
            "stock_id",
            name="uq_theme_mining_members_card_stock",
        ),
        comment="题材挖掘卡成份股明细",
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index(
        "idx_theme_mining_members_card_rank",
        "theme_mining_members",
        ["card_id", "rank"],
    )

    op.create_table(
        "theme_mining_notes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("card_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("content_md", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(length=200), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["card_id"],
            ["theme_mining_cards.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "card_id",
            "user_id",
            name="uq_theme_mining_notes_card_user",
        ),
        comment="题材挖掘卡用户模型点评",
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )


def downgrade() -> None:
    op.drop_table("theme_mining_notes")
    op.drop_index(
        "idx_theme_mining_members_card_rank",
        table_name="theme_mining_members",
    )
    op.drop_table("theme_mining_members")
    op.drop_index(
        "idx_theme_mining_cards_date_type_rank",
        table_name="theme_mining_cards",
    )
    op.drop_table("theme_mining_cards")
