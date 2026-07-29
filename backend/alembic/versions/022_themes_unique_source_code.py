"""themes: UNIQUE(code) -> UNIQUE(source, code) for multi-source storage."""

import sqlalchemy as sa
from alembic import op

revision = "022_themes_unique_source_code"
down_revision = "021_create_tushare_settings"
branch_labels = None
depends_on = None


def _index_names(table: str) -> set[str]:
    bind = op.get_bind()
    rows = bind.execute(sa.text(f"SHOW INDEX FROM `{table}`")).fetchall()
    # Key_name is typically index 2
    return {row[2] for row in rows}


def _has_unique_constraint(table: str, name: str) -> bool:
    bind = op.get_bind()
    row = bind.execute(
        sa.text(
            "SELECT CONSTRAINT_NAME FROM information_schema.TABLE_CONSTRAINTS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t "
            "AND CONSTRAINT_TYPE = 'UNIQUE' AND CONSTRAINT_NAME = :n"
        ),
        {"t": table, "n": name},
    ).fetchone()
    return row is not None


def upgrade() -> None:
    # 空 source 归一，避免唯一约束下多行 NULL 歧义
    op.execute(
        "UPDATE themes SET source = 'eastmoney' "
        "WHERE source IS NULL OR TRIM(source) = ''"
    )
    op.alter_column(
        "themes",
        "source",
        existing_type=sa.String(length=100),
        nullable=False,
        server_default="eastmoney",
        existing_nullable=True,
        existing_comment="数据来源",
    )

    indexes = _index_names("themes")
    # 去掉 code 全局唯一（MySQL 上 unique=True 生成的索引名通常为 code）
    if "code" in indexes:
        op.drop_index("code", table_name="themes")
        indexes.discard("code")
    if "ix_themes_code" not in indexes:
        op.create_index("ix_themes_code", "themes", ["code"])
    if not _has_unique_constraint("themes", "uq_themes_source_code"):
        op.create_unique_constraint(
            "uq_themes_source_code",
            "themes",
            ["source", "code"],
        )


def downgrade() -> None:
    if _has_unique_constraint("themes", "uq_themes_source_code"):
        op.drop_constraint("uq_themes_source_code", "themes", type_="unique")
    indexes = _index_names("themes")
    if "ix_themes_code" in indexes:
        op.drop_index("ix_themes_code", table_name="themes")
    if "code" not in indexes:
        # 降级前若存在同 code 多源行会失败——仅开发回滚用
        op.create_index("code", "themes", ["code"], unique=True)
    op.alter_column(
        "themes",
        "source",
        existing_type=sa.String(length=100),
        nullable=True,
        server_default=None,
        existing_nullable=False,
        existing_comment="数据来源",
    )
