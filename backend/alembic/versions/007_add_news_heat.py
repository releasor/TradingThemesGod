"""增加新闻热度字段。

Revision ID: 007_add_news_heat
Revises: 006_create_news_articles
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "007_add_news_heat"
down_revision: str | None = "006_create_news_articles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "news_articles",
        sa.Column("source_heat", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "news_articles",
        sa.Column("heat_score", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("news_articles", "heat_score")
    op.drop_column("news_articles", "source_heat")
