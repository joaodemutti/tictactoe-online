"""Add avatar_url to users.

Revision ID: 20260520_0005
Revises: 20260520_0004
Create Date: 2026-05-20 11:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260520_0005"
down_revision: Union[str, Sequence[str], None] = "20260520_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("avatar_url", sa.String(512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "avatar_url")
