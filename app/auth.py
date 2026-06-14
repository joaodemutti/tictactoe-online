from datetime import datetime, timedelta, timezone

import httpx
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.config import settings

COOKIE_NAME = "access_token"

_TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    return jwt.encode({"sub": user_id, "exp": expire}, settings.JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return payload.get("sub")
    except JWTError:
        return None


async def verify_turnstile(token: str, remoteip: str | None) -> bool:
    if not settings.TURNSTILE_SECRET_KEY:
        return True  # captcha disabled (dev) — skip verification
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(_TURNSTILE_VERIFY_URL, data={
                "secret": settings.TURNSTILE_SECRET_KEY,
                "response": token,
                "remoteip": remoteip,
            })
        return resp.json().get("success", False)
    except Exception:
        return False
