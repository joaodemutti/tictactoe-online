import asyncio
import json
import time
import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.database import AsyncSessionLocal
from app.deps import ws_get_current_user
from app.models import User
from app.services import game_service
from app.ws.chat import handle_send_message, handle_mark_read
from app.ws.manager import manager

router = APIRouter()

# In-memory role selection state — safe with a single Uvicorn worker
_pending_selections: dict[str, dict[str, str]] = {}   # match_id → {user_id: role}
_countdown_tasks:    dict[str, asyncio.Task]   = {}   # match_id → running Task
_countdown_start:    dict[str, float]          = {}   # match_id → time.monotonic() when countdown began


async def _resolve_after_delay(
    match_id: str, all_players: list[dict[str, str]]
) -> None:
    try:
        await asyncio.sleep(5)
    except asyncio.CancelledError:
        _countdown_start.pop(match_id, None)
        return

    selections  = _pending_selections.get(match_id, {})
    player_ids  = [p["user_id"] for p in all_players]
    roles       = game_service.resolve_roles(player_ids, selections)
    x_player_id = next(uid for uid, role in roles.items() if role == "x")
    match_uuid  = uuid.UUID(match_id)

    try:
        async with AsyncSessionLocal() as db:
            await game_service.assign_roles(db, match_uuid, roles, x_player_id)
    except Exception:
        pass

    await manager.broadcast_match(match_id, {
        "type":         "game_start",
        "roles":        roles,
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
        result = await game_service.apply_move(db, match_uuid, user_uuid, position)

    if result is None:
        return

    await manager.broadcast_match(match_id, {
        "type":      "move",
        "position":  position,
        "mark":      result["mark"],
        "next_turn": None if result["terminal"] else result["next_turn_id"],
    })

    if result["terminal"]:
        await manager.broadcast_match(match_id, {
            "type":      "game_over",
            "result":    "win" if result["winner_mark"] else "draw",
            "winner_id": user_id if result["winner_mark"] else None,
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

    old = _countdown_tasks.get(match_id)
    if old:
        old.cancel()

    all_selected = len(selections) == len(all_players)

    await manager.broadcast_match(match_id, {
        "type":         "role_selected",
        "user_id":      user_id,
        "role":         None if msg.get("unselect") is True else role,
        "selections":   selections,
        "countdown_ms": 5000 if all_selected else None,
    })

    if all_selected:
        _countdown_start[match_id] = time.monotonic()
        _countdown_tasks[match_id] = asyncio.create_task(
            _resolve_after_delay(match_id, all_players)
        )


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
        ws_data = await game_service.get_match_ws_data(db, match_id, user.id)

    if "error" in ws_data:
        await websocket.close(code=ws_data["error"])
        return

    all_players     = ws_data["all_players"]
    roles           = ws_data["roles"]
    roles_assigned  = ws_data["roles_assigned"]
    board           = ws_data["board"]
    current_turn_id = ws_data["current_turn_id"]
    was_waiting     = ws_data["was_waiting"]

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
            await game_service.set_match_active(db, match_id)

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
