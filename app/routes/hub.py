from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models import User
from app.services import user_service
from app.templating import _ctx, templates

router = APIRouter()


@router.get("/")
async def hub(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse(request, "hub.html", _ctx(request, user, user=user))


@router.get("/players/search")
async def search_players(
    q: str = Query("", max_length=20),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await user_service.search_players(db, q, page, limit, user.id)
