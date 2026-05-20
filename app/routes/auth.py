import io
import pathlib
import time

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.deps import get_current_user, get_db
from app.i18n import TRANSLATIONS, detect_language, get_translator
from app.models import User
from app.auth import hash_password, verify_password, create_access_token, COOKIE_NAME
from app.templating import templates

router = APIRouter()


def _ctx(request: Request, user=None, **extra):
    lang = detect_language(request, user)
    _ = get_translator(lang)
    return {"lang": lang, "_": _, "i18n": TRANSLATIONS[lang], **extra}


@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(request, "auth/login.html", _ctx(request))


@router.get("/signup")
async def signup_page(request: Request):
    return templates.TemplateResponse(request, "auth/signup.html", _ctx(request))


@router.post("/signup")
async def signup(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    avatar: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
):
    lang = detect_language(request)
    _ = get_translator(lang)

    result = await db.execute(
        select(User).where(or_(User.username == username, User.email == email))
    )
    if result.scalar_one_or_none():
        return templates.TemplateResponse(
            request,
            "auth/signup.html",
            _ctx(request, error=_("error_username_email_taken")),
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
                img = Image.open(io.BytesIO(data)).convert("RGB")
                w, h = img.size
                side = min(w, h)
                img = img.crop(((w - side) // 2, (h - side) // 2,
                                (w + side) // 2, (h + side) // 2))
                img = img.resize(_AVATAR_SIZE, Image.LANCZOS)
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
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password_hash):
        lang = detect_language(request)
        _ = get_translator(lang)
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            _ctx(request, error=_("error_invalid_credentials")),
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
    email = (body.get("email") or "").strip()
    password = body.get("password") or ""
    lang = body.get("language_code") or ""

    _ = get_translator(detect_language(request, current_user))

    if not username:
        return JSONResponse({"error": _("error_username_required")}, status_code=400)
    if not email:
        return JSONResponse({"error": _("error_email_required")}, status_code=400)

    result = await db.execute(
        select(User).where(
            User.id != current_user.id,
            or_(User.username == username, User.email == email),
        )
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


_AVATARS_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "static" / "avatars"
_AVATAR_SIZE = (128, 128)


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

    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        return JSONResponse({"error": _("error_invalid_image")}, status_code=400)

    # Center-crop to square then resize to avatar resolution
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side))
    img = img.resize(_AVATAR_SIZE, Image.LANCZOS)

    _AVATARS_DIR.mkdir(parents=True, exist_ok=True)
    dest = _AVATARS_DIR / f"{current_user.id}.webp"
    img.save(dest, format="WEBP", quality=85)

    avatar_url = f"/static/avatars/{current_user.id}.webp?t={int(time.time())}"
    current_user.avatar_url = avatar_url
    await db.commit()

    return JSONResponse({"ok": True, "avatar_url": avatar_url})
