"""新增用户表，并将模型配置按用户隔离。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "012_user_auth"
down_revision: str | None = "011_theme_insight_keys"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.execute(sa.text("DELETE FROM model_providers"))
    op.add_column(
        "model_providers",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
    )
    op.create_foreign_key(
        "fk_model_providers_user_id_users",
        "model_providers",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_model_providers_user_id", "model_providers", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_model_providers_user_id", table_name="model_providers")
    op.drop_constraint("fk_model_providers_user_id_users", "model_providers", type_="foreignkey")
    op.drop_column("model_providers", "user_id")
    op.drop_table("users")
