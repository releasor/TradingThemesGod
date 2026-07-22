"""创建模型服务配置。"""

import sqlalchemy as sa
from alembic import op

revision = "009_create_model_providers"
down_revision = "008_create_concept_graph"
branch_labels = None
depends_on = None


def upgrade() -> None:
    table = op.create_table(
        "model_providers",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("protocol", sa.String(30), nullable=False),
        sa.Column("base_url", sa.String(500), nullable=False),
        sa.Column("api_key_encrypted", sa.Text(), nullable=False),
        sa.Column("model", sa.String(200), nullable=False),
        sa.Column("custom_headers_encrypted", sa.Text(), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), server_default="60", nullable=False),
        sa.Column("temperature", sa.Numeric(3, 2), server_default="0.10", nullable=False),
        sa.Column("max_tokens", sa.Integer(), server_default="8192", nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"), mysql_engine="InnoDB", mysql_charset="utf8mb4",
    )
    op.bulk_insert(table, [{
        "name": "本地 CC-Switch", "protocol": "openai_compatible",
        "base_url": "http://127.0.0.1:15721/v1", "api_key_encrypted": "",
        "model": "gpt-5.6-sol", "custom_headers_encrypted": "",
        "timeout_seconds": 120, "temperature": 0.1, "max_tokens": 8192,
        "enabled": True, "is_default": True, "metadata_json": {"preset": True},
    }])


def downgrade() -> None:
    op.drop_table("model_providers")
