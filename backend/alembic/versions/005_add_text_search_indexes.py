"""添加文本搜索辅助索引

Revision ID: 005_add_text_search_indexes
Revises: 004_add_query_indexes
Create Date: 2026-07-13

名称索引已在初始迁移中创建。本迁移为 TEXT 描述字段创建 MySQL
前缀索引，支持前缀匹配并避免索引完整 TEXT 列。
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005_add_text_search_indexes"
down_revision: Union[str, None] = "004_add_query_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建 MySQL 文本前缀索引。"""
    op.create_index(
        "idx_theme_description_prefix",
        "themes",
        ["description"],
        mysql_length=191,
    )


def downgrade() -> None:
    """删除 MySQL 文本前缀索引。"""
    op.drop_index("idx_theme_description_prefix", table_name="themes")
