import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import or_, and_, select, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy import bindparam
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.deps import get_current_user, get_db
from app.models import Match, MatchPlayer, MatchStatus, Message, User

router = APIRouter()


@router.get("/messages/contacts")
async def get_contacts(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text("""
            WITH convos AS (
                SELECT
                    CASE WHEN sender_id = :uid THEN receiver_id ELSE sender_id END AS partner_id,
                    sender_id,
                    read_at
                FROM messages
                WHERE sender_id = :uid OR receiver_id = :uid
            )
            SELECT c.partner_id,
                   u.username,
                   u.avatar_url,
                   COUNT(*) FILTER (WHERE c.sender_id != :uid AND c.read_at IS NULL) AS unread_count
            FROM convos c
            JOIN users u ON u.id = c.partner_id
            GROUP BY c.partner_id, u.username, u.avatar_url
        """).bindparams(bindparam("uid", type_=PGUUID(as_uuid=True))),
        {"uid": user.id},
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


@router.get("/messages/{other_user_id}")
async def get_messages(
    other_user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Message)
        .where(
            or_(
                and_(Message.sender_id == user.id, Message.receiver_id == other_user_id),
                and_(Message.sender_id == other_user_id, Message.receiver_id == user.id),
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
            MatchPlayer.user_id == user.id,
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
        .join(MyPlayer, and_(MyPlayer.match_id == Match.id, MyPlayer.user_id == user.id))
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
                "match_id": str(match.id),
                "from_user_id": str(match.inviter_id) if match.inviter_id else None,
                "from_username": (
                    user.username if match.inviter_id == user.id
                    else None
                ),
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
