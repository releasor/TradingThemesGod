"""添加查询优化索引

Revision ID: 004_add_query_indexes
Revises: 003_add_filter_indexes
Create Date: 2026-07-13

为高频查询添加性能索引：
- themes.deleted_at: 普通索引，加速软删除过滤
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
    # MySQL 不支持 PostgreSQL 风格的部分索引，直接索引软删除字段。
    op.create_index(
        "idx_theme_deleted_at", "themes", ["deleted_at"]
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
    op.drop_index("idx_theme_deleted_at", table_name="themes")
