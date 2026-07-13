"""添加查询优化索引

Revision ID: 004_add_query_indexes
Revises: 003_add_filter_indexes
Create Date: 2026-07-13

为高频查询添加性能索引：
- themes.tags: GIN 索引，加速 JSONB .contains() 查询
- themes.deleted_at: 部分索引，加速软删除过滤
- themes.deleted_at + heat_index: 复合索引，加速热度排行查询
- events.stock_id + published_at DESC: 复合索引，加速 get_events_by_code
- scraper_runs.started_at: 索引，加速按时间排序查询
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004_add_query_indexes"
down_revision: Union[str, None] = "003_add_filter_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """添加查询优化索引"""
    # 1. GIN 索引：加速 Theme.tags JSONB .contains() 查询
    op.create_index(
        "idx_theme_tags", "themes", ["tags"], postgresql_using="gin"
    )

    # 2. 部分索引：加速所有过滤 deleted_at IS NULL 的查询
    op.execute(
        "CREATE INDEX idx_theme_deleted_at ON themes (id) WHERE deleted_at IS NULL"
    )

    # 3. 复合索引：加速热度排行查询
    op.create_index(
        "idx_theme_heat_ranking", "themes", ["deleted_at", "heat_index"]
    )

    # 4. 复合索引：加速 get_events_by_code（stock_id + published_at DESC）
    op.create_index(
        "idx_event_stock_published_at",
        "events",
        ["stock_id", "published_at"],
        postgresql_ops={"published_at": "DESC"},
    )

    # 5. 索引：加速 ScraperRun 按时间排序
    op.create_index(
        "idx_scraper_run_started", "scraper_runs", ["started_at"]
    )


def downgrade() -> None:
    """删除查询优化索引"""
    op.drop_index("idx_scraper_run_started", table_name="scraper_runs")
    op.drop_index("idx_event_stock_published_at", table_name="events")
    op.drop_index("idx_theme_heat_ranking", table_name="themes")
    op.execute("DROP INDEX idx_theme_deleted_at")
    op.drop_index("idx_theme_tags", table_name="themes")
