import json
from typing import Any

from fastapi import Request
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

from app.i18n import TRANSLATIONS, detect_language, get_translator

templates = Jinja2Templates(directory="templates")
templates.env.filters["tojson"] = lambda value: Markup(json.dumps(value, default=str))


def _ctx(request: Request, user: Any = None, **extra: Any) -> dict[str, Any]:
    lang = detect_language(request, user)
    _ = get_translator(lang)
    return {"lang": lang, "_": _, "i18n": TRANSLATIONS[lang], "user": user, **extra}
