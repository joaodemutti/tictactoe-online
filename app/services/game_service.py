import random
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.game.logic import check_winner, is_draw
from app.models import Match, MatchPlayer, MatchStatus, PlayerRole, Move, User


async def get_ongoing_matches(
    db: AsyncSession, user_id: uuid.UUID
) -> dict[str, str]:
    OtherMP = aliased(MatchPlayer)
    result = await db.execute(
        select(Match, OtherMP.user_id)
        .join(
            MatchPlayer,
            (MatchPlayer.match_id == Match.id) & (MatchPlayer.user_id == user_id),
        )
        .join(
            OtherMP,
            (OtherMP.match_id == Match.id) & (OtherMP.user_id != user_id),
        )
        .where(Match.status.in_([MatchStatus.waiting, MatchStatus.active]))
        .order_by(Match.created_at.desc())
    )
    ongoing: dict[str, str] = {}
    for match, other_user_id in result.all():
        ongoing.setdefault(str(other_user_id), str(match.id))
    return ongoing


async def find_or_create_invite(
    db: AsyncSession, inviter_id: uuid.UUID, target_id: uuid.UUID
) -> "tuple[Match, bool] | tuple[None, None]":
    """Return (match, is_new). match is None if target user not found."""
    result = await db.execute(select(User).where(User.id == target_id))
    if not result.scalar_one_or_none():
        return None, None

    my_match_ids    = select(MatchPlayer.match_id).where(MatchPlayer.user_id == inviter_id)
    their_match_ids = select(MatchPlayer.match_id).where(MatchPlayer.user_id == target_id)
    result = await db.execute(
        select(Match).where(
            Match.id.in_(my_match_ids),
            Match.id.in_(their_match_ids),
            Match.status.in_([MatchStatus.waiting, MatchStatus.active]),
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing, False

    match = Match(inviter_id=inviter_id)
    db.add(match)
    await db.flush()
    db.add(MatchPlayer(match_id=match.id, user_id=inviter_id, read_at=datetime.now(timezone.utc)))
    db.add(MatchPlayer(match_id=match.id, user_id=target_id))
    await db.commit()
    return match, True


async def mark_invite_read(
    db: AsyncSession, match_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    """Mark the invite as read. Returns False if the invite was not found."""
    result = await db.execute(
        select(MatchPlayer)
        .join(Match, Match.id == MatchPlayer.match_id)
        .where(
            MatchPlayer.match_id == match_id,
            MatchPlayer.user_id == user_id,
            Match.status == MatchStatus.waiting,
        )
    )
    if not result.scalar_one_or_none():
        return False
    await db.execute(
        update(MatchPlayer)
        .where(MatchPlayer.match_id == match_id, MatchPlayer.user_id == user_id)
        .values(read_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return True


async def get_match_page_data(
    db: AsyncSession, match_id: uuid.UUID, user_id: uuid.UUID
) -> tuple[Match | None, list | None]:
    """Return (match, players). match is None if not found; players is None if not authorized."""
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if not match:
        return None, None

    result = await db.execute(
        select(MatchPlayer).where(
            MatchPlayer.match_id == match_id,
            MatchPlayer.user_id == user_id,
        )
    )
    if not result.scalar_one_or_none():
        return match, None

    result = await db.execute(
        select(User)
        .join(MatchPlayer, MatchPlayer.user_id == User.id)
        .where(MatchPlayer.match_id == match_id)
    )
    players = [
        {"user_id": str(u.id), "username": u.username, "avatar_url": u.avatar_url}
        for u in result.scalars().all()
    ]
    return match, players


async def get_match_ws_data(
    db: AsyncSession, match_id: uuid.UUID, user_id: uuid.UUID
) -> dict:
    """Return board/role/player state for the WS connect, or {"error": 4004/4003}."""
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if not match:
        return {"error": 4004}

    result = await db.execute(
        select(MatchPlayer).where(
            MatchPlayer.match_id == match_id,
            MatchPlayer.user_id == user_id,
        )
    )
    if not result.scalar_one_or_none():
        return {"error": 4003}

    result = await db.execute(
        select(User)
        .join(MatchPlayer, MatchPlayer.user_id == User.id)
        .where(MatchPlayer.match_id == match_id)
    )
    all_players = [
        {"user_id": str(u.id), "username": u.username}
        for u in result.scalars().all()
    ]

    result = await db.execute(
        select(MatchPlayer).where(MatchPlayer.match_id == match_id)
    )
    mp_list = result.scalars().all()
    roles = {
        str(mp.user_id): mp.role.value if mp.role else None
        for mp in mp_list
    }

    return {
        "all_players":    all_players,
        "roles":          roles,
        "roles_assigned": any(role is not None for role in roles.values()),
        "board":          list(match.board),
        "current_turn_id": str(match.current_turn) if match.current_turn else None,
        "was_waiting":    match.status == MatchStatus.waiting,
    }


async def get_pending_invites(
    db: AsyncSession, user_id: uuid.UUID
) -> list[dict]:
    OtherMP   = aliased(MatchPlayer)
    OtherUser = aliased(User)
    result = await db.execute(
        select(Match, OtherUser)
        .join(MatchPlayer, (MatchPlayer.match_id == Match.id) & (MatchPlayer.user_id == user_id))
        .join(OtherMP,     (OtherMP.match_id == Match.id)     & (OtherMP.user_id != user_id))
        .join(OtherUser, OtherUser.id == OtherMP.user_id)
        .where(Match.status == MatchStatus.waiting, MatchPlayer.read_at.is_(None))
    )
    return [
        {
            "match_id":       str(m.id),
            "from_user_id":   str(u.id),
            "from_username":  u.username,
        }
        for m, u in result.all()
    ]


async def set_match_active(db: AsyncSession, match_id: uuid.UUID) -> None:
    await db.execute(
        update(Match).where(Match.id == match_id).values(status=MatchStatus.active)
    )
    await db.commit()


def resolve_roles(
    player_ids: list[str], selections: dict[str, str]
) -> dict[str, str]:
    vals = list(selections.values())
    if not vals or "random" in vals or (len(vals) == 2 and len(set(vals)) == 1):
        shuffled = random.sample(player_ids, 2)
        return {shuffled[0]: "x", shuffled[1]: "o"}
    result = dict(selections)
    for uid in player_ids:
        if uid not in result:
            used = set(result.values())
            result[uid] = next(r for r in ("x", "o") if r not in used)
    return result


async def assign_roles(
    db: AsyncSession,
    match_id: uuid.UUID,
    roles: dict[str, str],
    x_player_id: str,
) -> None:
    for uid, role in roles.items():
        await db.execute(
            update(MatchPlayer)
            .where(
                MatchPlayer.match_id == match_id,
                MatchPlayer.user_id  == uuid.UUID(uid),
            )
            .values(role=PlayerRole[role])
        )
    await db.execute(
        update(Match)
        .where(Match.id == match_id)
        .values(current_turn=uuid.UUID(x_player_id))
    )
    await db.commit()


async def apply_move(
    db: AsyncSession,
    match_id: uuid.UUID,
    user_id: uuid.UUID,
    position: int,
) -> dict | None:
    """Validate and apply a move. Returns move result dict, or None if the move is invalid."""
    result = await db.execute(
        select(Match).where(Match.id == match_id).with_for_update()
    )
    match = result.scalar_one_or_none()
    if not match or match.status != MatchStatus.active or match.current_turn != user_id:
        return None

    board = list(match.board)
    if board[position] is not None:
        return None

    result = await db.execute(
        select(MatchPlayer).where(
            MatchPlayer.match_id == match_id,
            MatchPlayer.user_id  == user_id,
        )
    )
    mp = result.scalar_one_or_none()
    if not mp or not mp.role:
        return None

    mark = mp.role.value.upper()

    result = await db.execute(
        select(MatchPlayer).where(
            MatchPlayer.match_id == match_id,
            MatchPlayer.user_id  != user_id,
        )
    )
    other_mp     = result.scalar_one_or_none()
    next_turn_id = str(other_mp.user_id) if other_mp else None

    board[position] = mark
    winner_mark = check_winner(board)
    terminal    = winner_mark is not None or is_draw(board)
    new_turn    = None if terminal else (uuid.UUID(next_turn_id) if next_turn_id else None)

    db.add(Move(match_id=match_id, player_id=user_id, position=position))
    await db.execute(
        update(Match)
        .where(Match.id == match_id)
        .values(
            board=board,
            current_turn=new_turn,
            status=MatchStatus.finished if terminal else MatchStatus.active,
            winner_id=user_id if winner_mark else None,
        )
    )
    await db.commit()

    return {
        "mark":         mark,
        "next_turn_id": next_turn_id,
        "terminal":     terminal,
        "winner_mark":  winner_mark,
    }
