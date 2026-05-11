"""baseline schema

Revision ID: 20260511_0001
Revises:
Create Date: 2026-05-11 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260511_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Baseline migration intentionally empty.
    pass


def downgrade() -> None:
    pass
