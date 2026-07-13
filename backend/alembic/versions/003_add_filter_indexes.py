"""添加筛选字段索引

Revision ID: 003_add_filter_indexes
Revises: 002_create_scraper_runs
Create Date: 2026-07-13

为频繁筛选的字段添加索引：
- themes.category: 按分类筛选
- stocks.industry: 按行业筛选
- stocks.exchange: 按交易所筛选
- events.event_type: 按事件类型筛选
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_add_filter_indexes"
down_revision: Union[str, None] = "002_create_scraper_runs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """添加筛选字段索引"""
    op.create_index("idx_theme_category", "themes", ["category"])
    op.create_index("idx_stock_industry", "stocks", ["industry"])
    op.create_index("idx_stock_exchange", "stocks", ["exchange"])
    op.create_index("idx_event_type", "events", ["event_type"])


def downgrade() -> None:
    """删除筛选字段索引"""
    op.drop_index("idx_event_type", table_name="events")
    op.drop_index("idx_stock_exchange", table_name="stocks")
    op.drop_index("idx_stock_industry", table_name="stocks")
    op.drop_index("idx_theme_category", table_name="themes")
