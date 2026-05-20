from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.deps import get_current_user, get_db
from app.models import User
from app.auth import hash_password, verify_password, create_access_token, COOKIE_NAME
from app.templating import templates

router = APIRouter()


@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(request, "auth/login.html")


@router.get("/signup")
async def signup_page(request: Request):
    return templates.TemplateResponse(request, "auth/signup.html")


@router.post("/signup")
async def signup(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(or_(User.username == username, User.email == email))
    )
    if result.scalar_one_or_none():
        return templates.TemplateResponse(
            request,
            "auth/signup.html",
            {"error": "Username or email already taken."},
            status_code=400,
        )

    user = User(username=username, email=email, password_hash=hash_password(password))
    db.add(user)
    await db.commit()
    await db.refresh(user)

    response = RedirectResponse("/", status_code=303)
    response.set_cookie(key=COOKIE_NAME, value=create_access_token(str(user.id)), httponly=True, samesite="lax")
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
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            {"error": "Invalid username or password."},
            status_code=401,
        )

    response = RedirectResponse("/", status_code=303)
    response.set_cookie(key=COOKIE_NAME, value=create_access_token(str(user.id)), httponly=True, samesite="lax")
    return response


@router.post("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(key=COOKIE_NAME)
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

    if not username:
        return JSONResponse({"error": "Username is required."}, status_code=400)
    if not email:
        return JSONResponse({"error": "Email is required."}, status_code=400)

    result = await db.execute(
        select(User).where(
            User.id != current_user.id,
            or_(User.username == username, User.email == email),
        )
    )
    if result.scalar_one_or_none():
        return JSONResponse(
            {"error": "Username or email already taken."},
            status_code=400,
        )

    current_user.username = username
    current_user.email = email
    if password.strip():
        current_user.password_hash = hash_password(password)

    await db.commit()

    return JSONResponse(
        {
            "ok": True,
            "username": current_user.username,
            "email": current_user.email,
        }
    )
