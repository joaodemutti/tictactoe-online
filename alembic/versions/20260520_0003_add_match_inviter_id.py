"""Add match inviter.

Revision ID: 20260520_0003
Revises: 20260520_0002
Create Date: 2026-05-20 03:05:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260520_0003"
down_revision: Union[str, Sequence[str], None] = "20260520_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("inviter_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_matches_inviter_id_users", "matches", "users", ["inviter_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_matches_inviter_id_users", "matches", type_="foreignkey")
    op.drop_column("matches", "inviter_id")
