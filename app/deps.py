import uuid

from fastapi import Depends, Request, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.auth import COOKIE_NAME, decode_token
from app.models import User


class RequiresLogin(Exception):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User:
    token = request.cookies.get(COOKIE_NAME)
    if token:
        user_id_str = decode_token(token)
        if user_id_str:
            try:
                user_id = uuid.UUID(user_id_str)
            except ValueError:
                raise RequiresLogin()
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                return user
    raise RequiresLogin()


async def ws_get_current_user(
    websocket: WebSocket, db: AsyncSession = Depends(get_db)
) -> User | None:
    token = websocket.cookies.get(COOKIE_NAME)
    if token:
        user_id_str = decode_token(token)
        if user_id_str:
            try:
                user_id = uuid.UUID(user_id_str)
            except ValueError:
                return None
            result = await db.execute(select(User).where(User.id == user_id))
            return result.scalar_one_or_none()
    return None
