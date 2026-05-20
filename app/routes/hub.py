from fastapi import APIRouter, Depends, Request

from app.deps import get_current_user
from app.i18n import TRANSLATIONS, detect_language, get_translator
from app.models import User
from app.templating import templates

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
