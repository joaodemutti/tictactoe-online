import json

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.database import AsyncSessionLocal
from app.deps import ws_get_current_user, ws_origin_allowed
from app.models import User
from app.services import game_service
from app.ws.chat import handle_send_message, handle_mark_read
from app.ws.manager import manager

router = APIRouter()


@router.websocket("/ws/hub")
async def hub_ws(
    websocket: WebSocket,
    user: User | None = Depends(ws_get_current_user),
) -> None:
    if not await ws_origin_allowed(websocket):
        return
    if user is None:
        await websocket.close(code=4001)
        return

    user_id = str(user.id)

    await manager.connect_hub(user_id, user.username, websocket, avatar_url=user.avatar_url)

    async with AsyncSessionLocal() as db:
        invites = await game_service.get_pending_invites(db, user.id)
    await manager.broadcast_presence()

    for invite in invites:
        await manager.send_to_user(user_id, {"type": "invite", **invite})

    try:
        while True:
            text = await websocket.receive_text()
            try:
                msg = json.loads(text)
            except (json.JSONDecodeError, ValueError):
                continue
            msg_type = msg.get("type")
            if msg_type == "send_message":
                await handle_send_message(user_id, user.username, msg)
            elif msg_type == "mark_read":
                await handle_mark_read(user_id, msg)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect_hub(user_id, websocket)
        await manager.broadcast_presence()
