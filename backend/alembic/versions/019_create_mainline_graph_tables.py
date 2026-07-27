"""创建主线图谱三表：mainline_graph_versions / nodes / edges。"""

import sqlalchemy as sa
from alembic import op

revision = "019_create_mainline_graph_tables"
down_revision = "018_create_theme_mining_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mainline_graph_versions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("parent_version_id", sa.BigInteger(), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=False),
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
            ["parent_version_id"],
            ["mainline_graph_versions.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        comment="主线图谱版本",
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index(
        "idx_mainline_graph_versions_date_kind_status",
        "mainline_graph_versions",
        ["trade_date", "kind", "status"],
    )

    op.create_table(
        "mainline_graph_nodes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("version_id", sa.BigInteger(), nullable=False),
        sa.Column("theme_id", sa.BigInteger(), nullable=False),
        sa.Column("mainline_score", sa.Integer(), nullable=False),
        sa.Column("strength_score", sa.Integer(), nullable=False),
        sa.Column("lifecycle_stage", sa.String(length=32), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["mainline_graph_versions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["theme_id"], ["themes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "version_id",
            "theme_id",
            name="uq_mainline_graph_nodes_version_theme",
        ),
        comment="主线图谱节点",
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )

    op.create_table(
        "mainline_graph_edges",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("version_id", sa.BigInteger(), nullable=False),
        sa.Column("from_theme_id", sa.BigInteger(), nullable=False),
        sa.Column("to_theme_id", sa.BigInteger(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("method", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["mainline_graph_versions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["from_theme_id"],
            ["themes.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["to_theme_id"],
            ["themes.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "version_id",
            "from_theme_id",
            "to_theme_id",
            name="uq_mainline_graph_edges_version_from_to",
        ),
        comment="主线图谱边",
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )


def downgrade() -> None:
    op.drop_table("mainline_graph_edges")
    op.drop_table("mainline_graph_nodes")
    op.drop_index(
        "idx_mainline_graph_versions_date_kind_status",
        table_name="mainline_graph_versions",
    )
    op.drop_table("mainline_graph_versions")
