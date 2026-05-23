import uuid
from datetime import datetime, timezone

from sqlalchemy import or_, and_, select, update, text, bindparam
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models import Match, MatchPlayer, MatchStatus, Message, User


async def get_contacts(db: AsyncSession, user_id: uuid.UUID) -> list[dict]:
    result = await db.execute(
        text("""
            WITH convos AS (
                SELECT
                    CASE WHEN sender_id = :uid THEN receiver_id ELSE sender_id END AS partner_id,
                    sender_id,
                    read_at
                FROM messages
                WHERE sender_id = :uid OR receiver_id = :uid
            ),
            match_partners AS (
                SELECT mp2.user_id AS partner_id
                FROM match_players mp1
                JOIN match_players mp2 ON mp1.match_id = mp2.match_id AND mp2.user_id != :uid
                WHERE mp1.user_id = :uid
            ),
            all_partners AS (
                SELECT partner_id FROM match_partners
                UNION
                SELECT partner_id FROM convos
            )
            SELECT ap.partner_id,
                   u.username,
                   u.avatar_url,
                   COUNT(*) FILTER (WHERE c.sender_id != :uid AND c.read_at IS NULL) AS unread_count
            FROM all_partners ap
            JOIN users u ON u.id = ap.partner_id
            LEFT JOIN convos c ON c.partner_id = ap.partner_id
            GROUP BY ap.partner_id, u.username, u.avatar_url
        """).bindparams(bindparam("uid", type_=PGUUID(as_uuid=True))),
        {"uid": user_id},
    )
    rows = result.mappings().all()
    return [
        {
            "user_id":      str(r["partner_id"]),
            "username":     r["username"],
            "avatar_url":   r["avatar_url"],
            "unread_count": int(r["unread_count"]),
        }
        for r in rows
    ]


async def get_thread(
    db: AsyncSession,
    user_id: uuid.UUID,
    other_user_id: uuid.UUID,
    user_username: str,
) -> dict:
    result = await db.execute(
        select(Message)
        .where(
            or_(
                and_(Message.sender_id == user_id,       Message.receiver_id == other_user_id),
                and_(Message.sender_id == other_user_id, Message.receiver_id == user_id),
            )
        )
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()

    their_match_ids = select(MatchPlayer.match_id).where(MatchPlayer.user_id == other_user_id)

    result = await db.execute(
        select(Match)
        .join(MatchPlayer, MatchPlayer.match_id == Match.id)
        .where(
            MatchPlayer.user_id == user_id,
            Match.id.in_(their_match_ids),
            Match.status.in_([MatchStatus.waiting, MatchStatus.active]),
        )
        .order_by(Match.created_at)
    )
    invites = result.scalars().all()

    WinnerUser = aliased(User)
    MyPlayer   = aliased(MatchPlayer)
    games_result = await db.execute(
        select(Match, MyPlayer.role.label("my_role"), WinnerUser.username.label("winner_username"))
        .join(MyPlayer, and_(MyPlayer.match_id == Match.id, MyPlayer.user_id == user_id))
        .outerjoin(WinnerUser, WinnerUser.id == Match.winner_id)
        .where(
            Match.id.in_(their_match_ids),
            Match.status == MatchStatus.finished,
        )
        .order_by(Match.created_at)
    )
    games = games_result.all()

    return {
        "messages": [
            {
                "id":         str(m.id),
                "sender_id":  str(m.sender_id),
                "content":    m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
        "invites": [
            {
                "match_id":      str(match.id),
                "from_user_id":  str(match.inviter_id) if match.inviter_id else None,
                "from_username": user_username if match.inviter_id == user_id else None,
            }
            for match in invites
        ],
        "games": [
            {
                "match_id":        str(match.id),
                "created_at":      match.created_at.isoformat(),
                "winner_id":       str(match.winner_id) if match.winner_id else None,
                "winner_username": winner_username,
                "my_role":         my_role.value if my_role else None,
            }
            for match, my_role, winner_username in games
        ],
    }


async def save_message(
    db: AsyncSession,
    sender_id: uuid.UUID,
    receiver_id: uuid.UUID,
    content: str,
) -> tuple[Message, User] | None:
    result = await db.execute(select(User).where(User.id == receiver_id))
    receiver = result.scalar_one_or_none()
    if not receiver:
        return None
    message = Message(sender_id=sender_id, receiver_id=receiver_id, content=content)
    db.add(message)
    await db.commit()
    return message, receiver


async def mark_messages_read(
    db: AsyncSession, sender_id: uuid.UUID, reader_id: uuid.UUID
) -> None:
    await db.execute(
        update(Message)
        .where(
            Message.sender_id   == sender_id,
            Message.receiver_id == reader_id,
            Message.read_at.is_(None),
        )
        .values(read_at=datetime.now(timezone.utc))
    )
    await db.commit()
