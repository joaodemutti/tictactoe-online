"""Full schema.

Revision ID: 0001_schema
Revises:
Create Date: 2026-05-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0001_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM("waiting", "active", "finished", name="matchstatus").create(bind, checkfirst=True)
    postgresql.ENUM("x", "o", name="playerrole").create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("language_code", sa.String(10), nullable=False, server_default="en"),
        sa.Column("avatar_url", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    op.create_table(
        "matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", postgresql.ENUM("waiting", "active", "finished", name="matchstatus", create_type=False), nullable=False),
        sa.Column("board", sa.JSON(), nullable=False),
        sa.Column("inviter_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("current_turn", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("winner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["inviter_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["current_turn"], ["users.id"]),
        sa.ForeignKeyConstraint(["winner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("receiver_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["receiver_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_messages_conversation", "messages", ["sender_id", "receiver_id"], unique=False)

    op.create_table(
        "match_players",
        sa.Column("match_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", postgresql.ENUM("x", "o", name="playerrole", create_type=False), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("match_id", "user_id"),
    )
    op.create_index("ix_match_players_user_id", "match_players", ["user_id"], unique=False)

    op.create_table(
        "moves",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("match_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("player_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("position >= 0 AND position <= 8", name="valid_position"),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"]),
        sa.ForeignKeyConstraint(["player_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_moves_match_id", "moves", ["match_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_moves_match_id", table_name="moves")
    op.drop_table("moves")
    op.drop_index("ix_match_players_user_id", table_name="match_players")
    op.drop_table("match_players")
    op.drop_index("ix_messages_conversation", table_name="messages")
    op.drop_table("messages")
    op.drop_table("matches")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_table("users")
    bind = op.get_bind()
    postgresql.ENUM("x", "o", name="playerrole").drop(bind, checkfirst=True)
    postgresql.ENUM("waiting", "active", "finished", name="matchstatus").drop(bind, checkfirst=True)
