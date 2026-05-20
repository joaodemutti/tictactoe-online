from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.i18n import TRANSLATIONS, detect_language, get_translator
from app.models import User
from app.templating import templates
from sqlalchemy import select, func

router = APIRouter()


@router.get("/")
async def hub(request: Request, user: User = Depends(get_current_user)):
    lang = detect_language(request, user)
    return templates.TemplateResponse(request, "hub.html", {
        "user": user,
        "lang": lang,
        "_": get_translator(lang),
        "i18n": TRANSLATIONS[lang],
    })


@router.get("/players/search")
async def search_players(
    q: str = Query("", max_length=20),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = q.strip()
    offset = (page - 1) * limit

    base = select(User).where(User.id != user.id)
    if q:
        base = base.where(User.username.ilike(f"%{q}%"))

    total_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = total_result.scalar()

    result = await db.execute(base.order_by(User.username).offset(offset).limit(limit))
    users = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "pages": max(1, (total + limit - 1) // limit),
        "results": [
            {"user_id": str(u.id), "username": u.username, "avatar_url": u.avatar_url}
            for u in users
        ],
    }
