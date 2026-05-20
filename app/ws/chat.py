import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update

from app.database import AsyncSessionLocal
from app.models import Message, User
from app.ws.manager import manager


async def handle_send_message(sender_id: str, sender_username: str, msg: dict) -> None:
    receiver_id = msg.get("receiver_id")
    content = msg.get("content", "").strip()
    if not receiver_id or not content:
        return

    try:
        receiver_uuid = uuid.UUID(receiver_id)
    except ValueError:
        return

    sender_uuid = uuid.UUID(sender_id)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == receiver_uuid))
        receiver = result.scalar_one_or_none()
        if not receiver:
            return

        message = Message(
            sender_id=sender_uuid,
            receiver_id=receiver_uuid,
            content=content,
        )
        db.add(message)
        await db.commit()

    payload = {
        "type":              "message",
        "id":                str(message.id),
        "sender_id":         sender_id,
        "sender_username":   sender_username,
        "receiver_id":       receiver_id,
        "receiver_username": receiver.username,
        "content":           content,
        "created_at":        message.created_at.isoformat(),
    }

    await manager.send_to_any(receiver_id, payload)
    await manager.send_to_any(sender_id, payload)


async def handle_mark_read(reader_id: str, msg: dict) -> None:
    sender_id = msg.get("sender_id")
    if not sender_id:
        return

    try:
        sender_uuid = uuid.UUID(sender_id)
        reader_uuid = uuid.UUID(reader_id)
    except ValueError:
        return

    async with AsyncSessionLocal() as db:
        await db.execute(
            update(Message)
            .where(
                Message.sender_id == sender_uuid,
                Message.receiver_id == reader_uuid,
                Message.read_at.is_(None),
            )
            .values(read_at=datetime.now(timezone.utc))
        )
        await db.commit()

    await manager.send_to_any(sender_id, {
        "type":      "message_read",
        "sender_id": sender_id,
        "reader_id": reader_id,
    })
