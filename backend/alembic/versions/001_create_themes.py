"""创建所有数据表

Revision ID: 001_create_themes
Revises:
Create Date: 2026-07-13

注意：
- updated_at 字段使用 server_default=now() 但没有 DDL 级别的 ON UPDATE 触发器
- 应用层通过 SQLAlchemy ORM 的 onupdate=func.now() 自动更新
- 如果使用原生 SQL 或批量操作，需要手动更新 updated_at
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_create_themes"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建所有表"""

    # 创建题材表
    op.create_table(
        "themes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False, comment="题材名称"),
        sa.Column("code", sa.String(50), nullable=False, unique=True, comment="题材代码"),
        sa.Column("description", sa.Text(), nullable=True, comment="题材描述"),
        sa.Column("heat_index", sa.Numeric(10, 2), nullable=False, server_default="0", comment="热度指数"),
        sa.Column("rise_fall_pct", sa.Numeric(8, 4), nullable=False, server_default="0", comment="涨跌幅(%)"),
        sa.Column("stock_count", sa.Integer(), nullable=False, server_default="0", comment="关联股票数量"),
        sa.Column("category", sa.String(50), nullable=True, comment="题材分类"),
        sa.Column("tags", sa.JSON(), nullable=True, comment="标签列表"),
        sa.Column("source", sa.String(100), nullable=True, comment="数据来源"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="软删除时间"),
        sa.PrimaryKeyConstraint("id"),
        comment="题材表",
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("idx_theme_name", "themes", ["name"])
    op.create_index("idx_theme_heat_index", "themes", ["heat_index"])

    # 创建股票表
    # 注意：code 字段有 UNIQUE 约束，MySQL 会自动创建索引
    op.create_table(
        "stocks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(20), nullable=False, unique=True, comment="股票代码"),
        sa.Column("name", sa.String(100), nullable=False, comment="股票名称"),
        sa.Column("industry", sa.String(100), nullable=True, comment="所属行业"),
        sa.Column("market_cap", sa.Numeric(20, 2), nullable=True, comment="总市值"),
        sa.Column("current_price", sa.Numeric(10, 2), nullable=True, comment="当前价格"),
        sa.Column("rise_fall_pct", sa.Numeric(8, 4), nullable=True, comment="涨跌幅(%)"),
        sa.Column("exchange", sa.String(20), nullable=True, comment="交易所(SH/SZ/BJ)"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        comment="股票表",
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("idx_stock_name", "stocks", ["name"])

    # 创建事件表
    op.create_table(
        "events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(200), nullable=False, comment="事件标题"),
        sa.Column("content", sa.Text(), nullable=True, comment="事件内容"),
        sa.Column("source", sa.String(100), nullable=True, comment="信息来源"),
        sa.Column("event_type", sa.String(50), nullable=True, comment="事件类型"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True, comment="发布时间"),
        sa.Column("stock_id", sa.BigInteger(), sa.ForeignKey("stocks.id", ondelete="SET NULL"), nullable=True, comment="关联股票ID"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        comment="事件表",
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("idx_event_stock_id", "events", ["stock_id"])
    op.create_index("idx_event_published_at", "events", ["published_at"])

    # 创建产业链表
    op.create_table(
        "industry_chains",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("theme_id", sa.BigInteger(), sa.ForeignKey("themes.id", ondelete="CASCADE"), nullable=False, comment="关联题材ID"),
        sa.Column("level", sa.String(20), nullable=False, comment="产业链层级(upstream/midstream/downstream)"),
        sa.Column("name", sa.String(100), nullable=False, comment="环节名称"),
        sa.Column("description", sa.Text(), nullable=True, comment="环节描述"),
        sa.Column("representative_companies", sa.JSON(), nullable=True, comment="代表公司列表"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0", comment="排序顺序"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "level IN ('upstream', 'midstream', 'downstream')",
            name="ck_industry_chain_level"
        ),
        comment="产业链表",
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("idx_industry_chain_theme_id", "industry_chains", ["theme_id"])

    # 创建题材-股票关联表
    op.create_table(
        "theme_stocks",
        sa.Column("theme_id", sa.BigInteger(), sa.ForeignKey("themes.id", ondelete="CASCADE"), nullable=False, comment="题材ID"),
        sa.Column("stock_id", sa.BigInteger(), sa.ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, comment="股票ID"),
        sa.Column("chain_level", sa.String(20), nullable=True, comment="产业链层级"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0", comment="排序顺序"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("theme_id", "stock_id", name="pk_theme_stocks"),
        comment="题材-股票关联表",
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("idx_theme_stocks_stock_id", "theme_stocks", ["stock_id"])


def downgrade() -> None:
    """删除所有表"""
    op.drop_table("theme_stocks")
    op.drop_table("industry_chains")
    op.drop_table("events")
    op.drop_table("stocks")
    op.drop_table("themes")
