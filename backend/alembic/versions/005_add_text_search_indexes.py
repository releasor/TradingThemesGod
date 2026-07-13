"""添加 pg_trgm 全文搜索索引

Revision ID: 005_add_text_search_indexes
Revises: 004_add_query_indexes
Create Date: 2026-07-13

启用 pg_trgm 扩展并创建 GIN 索引，使 ILIKE 查询能利用索引加速：
- themes.name: GIN trigram 索引
- themes.description: GIN trigram 索引
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005_add_text_search_indexes"
down_revision: Union[str, None] = "004_add_query_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """启用 pg_trgm 扩展并创建 GIN 索引"""
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX idx_theme_name_trgm ON themes USING GIN (name gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX idx_theme_description_trgm ON themes USING GIN (description gin_trgm_ops)"
    )


def downgrade() -> None:
    """删除 trigram 索引和扩展"""
    op.execute("DROP INDEX IF EXISTS idx_theme_description_trgm")
    op.execute("DROP INDEX IF EXISTS idx_theme_name_trgm")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
