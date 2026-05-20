"""Add language_code to users.

Revision ID: 20260520_0004
Revises: 20260520_0003
Create Date: 2026-05-20 10:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260520_0004"
down_revision: Union[str, Sequence[str], None] = "20260520_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("language_code", sa.String(10), nullable=False, server_default="en"),
    )


def downgrade() -> None:
    op.drop_column("users", "language_code")
