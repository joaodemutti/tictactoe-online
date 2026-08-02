import io
import pathlib
import time

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.config import settings
from app.deps import get_current_user, get_db
from app.i18n import TRANSLATIONS, detect_language, get_translator
from app.models import User
from app.auth import hash_password, verify_password, create_access_token, verify_turnstile, COOKIE_NAME
from app.templating import _ctx, templates

_AVATARS_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "static" / "avatars"
_AVATAR_SIZE = (128, 128)

router = APIRouter()


@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(
        request, "auth/login.html", _ctx(request, site_key=settings.TURNSTILE_SITE_KEY)
    )


@router.get("/signup")
async def signup_page(request: Request):
    return templates.TemplateResponse(
        request, "auth/signup.html", _ctx(request, site_key=settings.TURNSTILE_SITE_KEY)
    )


@router.post("/signup")
async def signup(
    request: Request,
    username: str = Form(...),
    email: str | None = Form(None),
    password: str = Form(...),
    avatar: UploadFile = File(None),
    cf_turnstile_response: str = Form("", alias="cf-turnstile-response"),
    db: AsyncSession = Depends(get_db),
):
    lang = detect_language(request)
    _ = get_translator(lang)

    if not await verify_turnstile(cf_turnstile_response):
        return templates.TemplateResponse(
            request, "auth/signup.html",
            _ctx(request, error=_("error_captcha_failed"), site_key=settings.TURNSTILE_SITE_KEY),
            status_code=400,
        )

    email = email.strip() if email else None
    email = email or None

    if len(username) > 20:
        return templates.TemplateResponse(
            request, "auth/signup.html",
            _ctx(request, error=_("error_username_too_long"), site_key=settings.TURNSTILE_SITE_KEY),
            status_code=400,
        )

    conditions = [User.username == username]
    if email:
        conditions.append(User.email == email)
    result = await db.execute(select(User).where(or_(*conditions)))
    if result.scalar_one_or_none():
        return templates.TemplateResponse(
            request,
            "auth/signup.html",
            _ctx(request, error=_("error_username_email_taken"), site_key=settings.TURNSTILE_SITE_KEY),
            status_code=400,
        )

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        language_code=lang,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    if avatar and avatar.filename:
        try:
            data = await avatar.read()
            if data and len(data) <= 5 * 1024 * 1024:
                img = _process_avatar(data)
                if img:
                    _AVATARS_DIR.mkdir(parents=True, exist_ok=True)
                    img.save(_AVATARS_DIR / f"{user.id}.webp", format="WEBP", quality=85)
                    user.avatar_url = f"/static/avatars/{user.id}.webp?t={int(time.time())}"
                    await db.commit()
        except Exception:
            pass  # avatar is optional — don't block signup on image errors

    response = RedirectResponse("/", status_code=303)
    response.set_cookie(key=COOKIE_NAME, value=create_access_token(str(user.id)), httponly=True, samesite="lax")
    response.set_cookie(key="lang", value=lang, samesite="lax")
    return response


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    cf_turnstile_response: str = Form("", alias="cf-turnstile-response"),
    db: AsyncSession = Depends(get_db),
):
    if not await verify_turnstile(cf_turnstile_response):
        lang = detect_language(request)
        _ = get_translator(lang)
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            _ctx(request, error=_("error_captcha_failed"), site_key=settings.TURNSTILE_SITE_KEY),
            status_code=400,
        )

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password_hash):
        lang = detect_language(request)
        _ = get_translator(lang)
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            _ctx(request, error=_("error_invalid_credentials"), site_key=settings.TURNSTILE_SITE_KEY),
            status_code=401,
        )

    response = RedirectResponse("/", status_code=303)
    response.set_cookie(key=COOKIE_NAME, value=create_access_token(str(user.id)), httponly=True, samesite="lax")
    response.set_cookie(key="lang", value=user.language_code, samesite="lax")
    return response


@router.post("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(key=COOKIE_NAME)
    return response


@router.post("/language")
async def set_language(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    body = await request.json()
    lang = body.get("lang", "en")
    if lang not in TRANSLATIONS:
        lang = "en"

    try:
        user: User = await get_current_user(request, db)
        user.language_code = lang
        await db.commit()
    except Exception:
        pass

    response = JSONResponse({"ok": True})
    response.set_cookie(key="lang", value=lang, samesite="lax")
    return response


@router.post("/profile")
async def update_profile(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    body = await request.json()
    username = (body.get("username") or "").strip()
    email = (body.get("email") or "").strip() or None
    password = body.get("password") or ""
    lang = body.get("language_code") or ""

    _ = get_translator(detect_language(request, current_user))

    if not username:
        return JSONResponse({"error": _("error_username_required")}, status_code=400)
    if len(username) > 20:
        return JSONResponse({"error": _("error_username_too_long")}, status_code=400)

    conditions = [User.username == username]
    if email:
        conditions.append(User.email == email)
    result = await db.execute(
        select(User).where(User.id != current_user.id, or_(*conditions))
    )
    if result.scalar_one_or_none():
        return JSONResponse({"error": _("error_username_email_taken")}, status_code=400)

    current_user.username = username
    current_user.email = email
    if password.strip():
        current_user.password_hash = hash_password(password)
    if lang in TRANSLATIONS:
        current_user.language_code = lang

    await db.commit()

    response = JSONResponse({
        "ok": True,
        "username": current_user.username,
        "email": current_user.email,
        "language_code": current_user.language_code,
    })
    response.set_cookie(key="lang", value=current_user.language_code, samesite="lax")
    return response


def _process_avatar(data: bytes) -> "Image.Image | None":
    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        return None
    w, h = img.size
    side = min(w, h)
    img = img.crop(((w - side) // 2, (h - side) // 2, (w + side) // 2, (h + side) // 2))
    return img.resize(_AVATAR_SIZE, Image.LANCZOS)


@router.post("/profile/avatar")
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = get_translator(detect_language(request, current_user))

    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        return JSONResponse({"error": _("error_image_too_large")}, status_code=400)

    img = _process_avatar(data)
    if img is None:
        return JSONResponse({"error": _("error_invalid_image")}, status_code=400)

    _AVATARS_DIR.mkdir(parents=True, exist_ok=True)
    dest = _AVATARS_DIR / f"{current_user.id}.webp"
    img.save(dest, format="WEBP", quality=85)

    avatar_url = f"/static/avatars/{current_user.id}.webp?t={int(time.time())}"
    current_user.avatar_url = avatar_url
    await db.commit()

    return JSONResponse({"ok": True, "avatar_url": avatar_url})
