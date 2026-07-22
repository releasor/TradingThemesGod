"""创建递归概念知识图谱。"""

import sqlalchemy as sa
from alembic import op

revision = "008_create_concept_graph"
down_revision = "007_add_news_heat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "concept_nodes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("theme_id", sa.BigInteger(), nullable=False),
        sa.Column("parent_id", sa.BigInteger(), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("path_key", sa.String(500), nullable=False),
        sa.Column("node_type", sa.String(30), server_default="segment", nullable=False),
        sa.Column("description", sa.Text()), sa.Column("chain_level", sa.String(20)),
        sa.Column("market_logic", sa.Text()), sa.Column("catalysts", sa.JSON(), nullable=False),
        sa.Column("risks", sa.JSON(), nullable=False), sa.Column("sources", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), server_default="0", nullable=False),
        sa.Column("depth", sa.Integer(), server_default="0", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["theme_id"], ["themes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["concept_nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"), mysql_engine="InnoDB", mysql_charset="utf8mb4",
    )
    op.create_index("idx_concept_node_theme_parent", "concept_nodes", ["theme_id", "parent_id"])
    op.create_index("idx_concept_node_theme_path", "concept_nodes", ["theme_id", "path_key"], unique=True)
    op.create_table(
        "concept_node_stocks",
        sa.Column("node_id", sa.BigInteger(), nullable=False), sa.Column("stock_id", sa.BigInteger(), nullable=False),
        sa.Column("relation_type", sa.String(50), nullable=False), sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("relevance_score", sa.Numeric(4, 3), server_default="0", nullable=False),
        sa.Column("is_core", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("sources", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["node_id"], ["concept_nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("node_id", "stock_id", name="pk_concept_node_stocks"),
        mysql_engine="InnoDB", mysql_charset="utf8mb4",
    )
    op.create_index("idx_concept_node_stock_stock_id", "concept_node_stocks", ["stock_id"])


def downgrade() -> None:
    op.drop_table("concept_node_stocks")
    op.drop_table("concept_nodes")
