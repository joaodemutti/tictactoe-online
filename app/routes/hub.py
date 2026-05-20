from fastapi import APIRouter, Depends, Request

from app.deps import get_current_user
from app.models import User
from app.templating import templates

router = APIRouter()


@router.get("/")
async def hub(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse(request, "hub.html", {"user": user})
