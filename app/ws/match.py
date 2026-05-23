import asyncio
import json
import random
import time
import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import select, update

from app.database import AsyncSessionLocal
from app.deps import ws_get_current_user
from app.game.logic import check_winner, is_draw
from app.models import User, Match, MatchPlayer, MatchStatus, PlayerRole, Move
from app.ws.chat import handle_send_message, handle_mark_read
from app.ws.manager import manager

router = APIRouter()

# In-memory role selection state — safe with a single Uvicorn worker
_pending_selections: dict[str, dict[str, str]] = {}   # match_id → {user_id: role}
_countdown_tasks:    dict[str, asyncio.Task]   = {}   # match_id → running Task
_countdown_start:    dict[str, float]          = {}   # match_id → time.monotonic() when countdown began


# ── Role resolution ───────────────────────────────────────────────────────────

def _resolve_roles(player_ids: list[str], selections: dict[str, str]) -> dict[str, str]:
    vals = list(selections.values())

    # No selections, any "random", or both picked the same → coin flip
    if not vals or "random" in vals or (len(vals) == 2 and len(set(vals)) == 1):
        shuffled = random.sample(player_ids, 2)
        return {shuffled[0]: "x", shuffled[1]: "o"}

    # Honor explicit different picks; fill in anyone who didn't pick
    result = dict(selections)
    for uid in player_ids:
        if uid not in result:
            used = set(result.values())
            result[uid] = next(r for r in ("x", "o") if r not in used)
    return result


async def _resolve_after_delay(
    match_id: str, all_players: list[dict[str, str]]
) -> None:
    try:
        await asyncio.sleep(5)
    except asyncio.CancelledError:
        _countdown_start.pop(match_id, None)
        return  # A player changed selection — new task will be started

    selections = _pending_selections.get(match_id, {})
    player_ids = [p["user_id"] for p in all_players]
    roles = _resolve_roles(player_ids, selections)

    x_player_id = next(uid for uid, role in roles.items() if role == "x")
    match_uuid  = uuid.UUID(match_id)

    try:
        async with AsyncSessionLocal() as db:
            for uid, role in roles.items():
                await db.execute(
                    update(MatchPlayer)
                    .where(
                        MatchPlayer.match_id == match_uuid,
                        MatchPlayer.user_id  == uuid.UUID(uid),
                    )
                    .values(role=PlayerRole[role])
                )
            await db.execute(
                update(Match)
                .where(Match.id == match_uuid)
                .values(current_turn=uuid.UUID(x_player_id))
            )
            await db.commit()
    except Exception:
        pass

    await manager.broadcast_match(match_id, {
        "type": "game_start",
        "roles": roles,
        "current_turn": x_player_id,
    })

    _pending_selections.pop(match_id, None)
    _countdown_tasks.pop(match_id, None)
    _countdown_start.pop(match_id, None)


async def _handle_move(match_id: str, user_id: str, msg: dict) -> None:
    position = msg.get("position")
    if not isinstance(position, int) or not (0 <= position <= 8):
        return

    match_uuid = uuid.UUID(match_id)
    user_uuid  = uuid.UUID(user_id)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Match).where(Match.id == match_uuid).with_for_update()
        )
        match = result.scalar_one_or_none()
        if not match:
            return
        if match.status != MatchStatus.active:
            return
        if match.current_turn != user_uuid:
            return

        board = list(match.board)
        if board[position] is not None:
            return

        result = await db.execute(
            select(MatchPlayer).where(
                MatchPlayer.match_id == match_uuid,
                MatchPlayer.user_id  == user_uuid,
            )
        )
        mp = result.scalar_one_or_none()
        if not mp or not mp.role:
            return

        mark = mp.role.value.upper()  # "X" or "O"

        result = await db.execute(
            select(MatchPlayer).where(
                MatchPlayer.match_id == match_uuid,
                MatchPlayer.user_id  != user_uuid,
            )
        )
        other_mp     = result.scalar_one_or_none()
        next_turn_id = str(other_mp.user_id) if other_mp else None

        board[position] = mark
        winner_mark = check_winner(board)
        terminal    = winner_mark is not None or is_draw(board)
        new_turn    = None if terminal else (uuid.UUID(next_turn_id) if next_turn_id else None)

        db.add(Move(match_id=match_uuid, player_id=user_uuid, position=position))
        await db.execute(
            update(Match)
            .where(Match.id == match_uuid)
            .values(
                board=board,
                current_turn=new_turn,
                status=MatchStatus.finished if terminal else MatchStatus.active,
                winner_id=user_uuid if winner_mark else None,
            )
        )
        await db.commit()

    await manager.broadcast_match(match_id, {
        "type":      "move",
        "position":  position,
        "mark":      mark,
        "next_turn": None if terminal else next_turn_id,
    })

    if terminal:
        await manager.broadcast_match(match_id, {
            "type":      "game_over",
            "result":    "win" if winner_mark else "draw",
            "winner_id": str(user_uuid) if winner_mark else None,
        })


async def _handle_role_select(
    match_id: str, user_id: str, msg: dict, all_players: list[dict[str, str]]
) -> None:
    role = msg.get("role")
    if role not in ("x", "o", "random"):
        return

    selections = _pending_selections.setdefault(match_id, {})
    if msg.get("unselect") is True:
        selections.pop(user_id, None)
    else:
        selections[user_id] = role

    # Cancel existing countdown and start a fresh 5-second one
    old = _countdown_tasks.get(match_id)
    if old:
        old.cancel()

    all_selected = len(selections) == len(all_players)

    await manager.broadcast_match(match_id, {
        "type": "role_selected",
        "user_id": user_id,
        "role": None if msg.get("unselect") is True else role,
        "selections": selections,
        "countdown_ms": 5000 if all_selected else None,
    })

    if all_selected:
        _countdown_start[match_id] = time.monotonic()
        _countdown_tasks[match_id] = asyncio.create_task(
            _resolve_after_delay(match_id, all_players)
        )


# ── WebSocket endpoint ────────────────────────────────────────────────────────

@router.websocket("/ws/match/{match_id}")
async def match_ws(
    websocket: WebSocket,
    match_id: uuid.UUID,
    user: User | None = Depends(ws_get_current_user),
) -> None:
    if user is None:
        await websocket.close(code=4001)
        return

    match_id_str = str(match_id)
    user_id_str  = str(user.id)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Match).where(Match.id == match_id))
        match = result.scalar_one_or_none()
        if not match:
            await websocket.close(code=4004)
            return

        result = await db.execute(
            select(MatchPlayer).where(
                MatchPlayer.match_id == match_id,
                MatchPlayer.user_id  == user.id,
            )
        )
        if not result.scalar_one_or_none():
            await websocket.close(code=4003)
            return

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
        roles_assigned    = any(role is not None for role in roles.values())

        board            = list(match.board)
        current_turn_id  = str(match.current_turn) if match.current_turn else None
        was_waiting      = match.status == MatchStatus.waiting

    await manager.connect_match(match_id_str, user_id_str, user.username, websocket)
    await manager.broadcast_presence()

    countdown_ms = None
    if match_id_str in _countdown_start:
        elapsed_ms = (time.monotonic() - _countdown_start[match_id_str]) * 1000
        remaining  = max(0, 5000 - elapsed_ms)
        if remaining > 0:
            countdown_ms = remaining

    await manager.send_to_match_user(match_id_str, user_id_str, {
        "type":         "board_state",
        "board":        board,
        "players":      all_players,
        "roles":        roles,
        "selections":   _pending_selections.get(match_id_str, {}),
        "current_turn": current_turn_id,
        "countdown_ms": countdown_ms,
    })

    connected_ids = manager.match_user_ids(match_id_str)
    both_present  = len(connected_ids) == 2

    if both_present and was_waiting:
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(Match).where(Match.id == match_id).values(status=MatchStatus.active)
            )
            await db.commit()

    connected_players = [p for p in all_players if p["user_id"] in connected_ids]
    await manager.broadcast_match(match_id_str, {
        "type":              "player_joined",
        "user_id":           user_id_str,
        "username":          user.username,
        "connected_players": connected_players,
        "both_present":      both_present,
        "roles_needed":      both_present and not roles_assigned,
    })

    try:
        while True:
            text = await websocket.receive_text()
            try:
                msg = json.loads(text)
            except (json.JSONDecodeError, ValueError):
                continue

            msg_type = msg.get("type")
            if msg_type == "role_select":
                await _handle_role_select(match_id_str, user_id_str, msg, all_players)
            elif msg_type == "move":
                await _handle_move(match_id_str, user_id_str, msg)
            elif msg_type == "send_message":
                await handle_send_message(user_id_str, user.username, msg)
            elif msg_type == "mark_read":
                await handle_mark_read(user_id_str, msg)

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect_match(match_id_str, user_id_str, websocket)
        await manager.broadcast_presence()
