import logging
from datetime import datetime, timedelta, timezone

import httpx
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.config import settings

COOKIE_NAME = "access_token"

_log = logging.getLogger(__name__)

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


async def verify_turnstile(token: str) -> bool:
    if not settings.TURNSTILE_SECRET_KEY:
        return True  # captcha disabled (dev) — skip verification
    if not token:
        return False
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(_TURNSTILE_VERIFY_URL, data={
                "secret": settings.TURNSTILE_SECRET_KEY,
                "response": token,
            })
        # NOTE: we intentionally do NOT send `remoteip`. Cloudflare ties the
        # token to the IP that solved the challenge, and iOS clients (iCloud
        # Private Relay / rotating cellular IPv6) frequently egress from a
        # different IP by verification time, which made valid tokens fail.
        result = resp.json()
        if not result.get("success", False):
            _log.warning("turnstile verification failed: %s", result.get("error-codes"))
        return result.get("success", False)
    except Exception:
        _log.exception("turnstile verification request errored")
        return False
