"""Add props_needed to schedule_items

Revision ID: da4fc4d98c2c
Revises: 20260511_0001
Create Date: 2026-05-18 06:06:10.234286
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "da4fc4d98c2c"
down_revision: Union[str, None] = "20260511_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "schedule_items",
        sa.Column("props_needed", sa.Text(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("schedule_items", "props_needed")
