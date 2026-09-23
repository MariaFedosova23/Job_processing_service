"""add cancelled status

Revision ID: 38ba48206a4b
Revises: 8fd6da0f8923
Create Date: 2026-09-23 12:50:43.341760

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '38ba48206a4b'
down_revision: Union[str, Sequence[str], None] = '8fd6da0f8923'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint("ck_tasks_status", "tasks", type_="check")
    op.create_check_constraint(
        "ck_tasks_status",
        "tasks",
        "status IN ('new', 'queued', 'processing', 'done', 'error', 'cancelled', 'retry')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_tasks_status", "tasks", type_="check")
    op.create_check_constraint(
        "ck_tasks_status",
        "tasks",
        "status IN ('new', 'queued', 'processing', 'done', 'error')",
    )
