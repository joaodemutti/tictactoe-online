import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Integer, Text,
    Enum as SAEnum, JSON, CheckConstraint, Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class MatchStatus(str, enum.Enum):
    waiting = "waiting"
    active = "active"
    finished = "finished"


class PlayerRole(str, enum.Enum):
    x = "x"
    o = "o"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    language_code = Column(String(10), nullable=False, default="en")
    avatar_url = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)

    match_players = relationship("MatchPlayer", back_populates="user")
    moves = relationship("Move", back_populates="player")
    sent_messages = relationship(
        "Message", back_populates="sender", foreign_keys="[Message.sender_id]"
    )
    received_messages = relationship(
        "Message", back_populates="receiver", foreign_keys="[Message.receiver_id]"
    )


class Match(Base):
    __tablename__ = "matches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(
        SAEnum(MatchStatus, name="matchstatus"),
        nullable=False,
        default=MatchStatus.waiting,
    )
    board = Column(JSON, nullable=False, default=lambda: [None] * 9)
    inviter_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    current_turn = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    winner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)

    players = relationship("MatchPlayer", back_populates="match")
    moves = relationship("Move", back_populates="match")


class MatchPlayer(Base):
    __tablename__ = "match_players"
    __table_args__ = (
        Index("ix_match_players_user_id", "user_id"),
    )

    match_id = Column(UUID(as_uuid=True), ForeignKey("matches.id"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    role = Column(SAEnum(PlayerRole, name="playerrole"), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    joined_at = Column(DateTime(timezone=True), nullable=False, default=_now)

    match = relationship("Match", back_populates="players")
    user = relationship("User", back_populates="match_players")


class Move(Base):
    __tablename__ = "moves"
    __table_args__ = (
        CheckConstraint("position >= 0 AND position <= 8", name="valid_position"),
        Index("ix_moves_match_id", "match_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id = Column(UUID(as_uuid=True), ForeignKey("matches.id"), nullable=False)
    player_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    position = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)

    match = relationship("Match", back_populates="moves")
    player = relationship("User", back_populates="moves")


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_conversation", "sender_id", "receiver_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    receiver_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    read_at = Column(DateTime(timezone=True), nullable=True)

    sender = relationship("User", back_populates="sent_messages", foreign_keys=[sender_id])
    receiver = relationship(
        "User", back_populates="received_messages", foreign_keys=[receiver_id]
    )
