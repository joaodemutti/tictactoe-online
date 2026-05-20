import json

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import aliased

from app.database import AsyncSessionLocal
from app.deps import ws_get_current_user
from app.models import User, Match, MatchPlayer, MatchStatus
from app.ws.chat import handle_send_message, handle_mark_read
from app.ws.manager import manager

router = APIRouter()


@router.websocket("/ws/hub")
async def hub_ws(
    websocket: WebSocket,
    user: User | None = Depends(ws_get_current_user),
) -> None:
    if user is None:
        await websocket.close(code=4001)
        return

    user_id = str(user.id)

    await manager.connect_hub(user_id, user.username, websocket, avatar_url=user.avatar_url)
    await manager.broadcast_presence()

    # Send any pending invites the user may have missed while offline
    async with AsyncSessionLocal() as db:
        OtherMP = aliased(MatchPlayer)
        OtherUser = aliased(User)
        result = await db.execute(
            select(Match, OtherUser)
            .join(MatchPlayer, (MatchPlayer.match_id == Match.id) & (MatchPlayer.user_id == user.id))
            .join(OtherMP, (OtherMP.match_id == Match.id) & (OtherMP.user_id != user.id))
            .join(OtherUser, OtherUser.id == OtherMP.user_id)
            .where(Match.status == MatchStatus.waiting, MatchPlayer.read_at.is_(None))
        )
        for match_obj, other_user_obj in result.all():
            await manager.send_to_user(user_id, {
                "type": "invite",
                "match_id": str(match_obj.id),
                "from_user_id": str(other_user_obj.id),
                "from_username": other_user_obj.username,
            })

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
