import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models import User
from app.services import message_service

router = APIRouter()


@router.get("/messages/contacts")
async def get_contacts(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await message_service.get_contacts(db, user.id)


@router.get("/messages/{other_user_id}")
async def get_messages(
    other_user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await message_service.get_thread(db, user.id, other_user_id, user.username)
