"""为个人 AI OS 档案增加决策调参附录。"""

import sqlalchemy as sa
from alembic import op

revision = "025_add_os_decision_prompt_appendix"
down_revision = "024_create_personal_os_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "os_profiles",
        sa.Column("decision_prompt_appendix", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("os_profiles", "decision_prompt_appendix")
