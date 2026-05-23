import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, get_current_user
from app.i18n import TRANSLATIONS, detect_language, get_translator
from app.models import User
from app.services import game_service
from app.templating import templates
from app.ws.manager import manager

router = APIRouter()


@router.get("/match/ongoing")
async def get_ongoing_matches(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ongoing = await game_service.get_ongoing_matches(db, current_user.id)
    return {"matches": ongoing}


@router.post("/match/invite")
async def create_invite(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    body = await request.json()
    try:
        target_id = uuid.UUID(body["target_user_id"])
    except (KeyError, ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid target_user_id")

    if target_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot invite yourself")

    match, is_new = await game_service.find_or_create_invite(db, current_user.id, target_id)
    if match is None:
        raise HTTPException(status_code=404, detail="User not found")

    if not is_new:
        return JSONResponse({
            "match_id": str(match.id),
            "existing": True,
            "from_user_id": str(match.inviter_id) if match.inviter_id else None,
        })

    await manager.send_to_any(str(target_id), {
        "type": "invite",
        "match_id": str(match.id),
        "from_user_id": str(current_user.id),
        "from_username": current_user.username,
    })

    return JSONResponse({"match_id": str(match.id), "existing": False})


@router.post("/match/invite/{match_id}/read")
async def mark_invite_read(
    match_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    found = await game_service.mark_invite_read(db, match_id, current_user.id)
    if not found:
        raise HTTPException(status_code=404, detail="Invite not found")
    return JSONResponse({"ok": True})


@router.get("/match/{match_id}")
async def match_page(
    match_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    match, players = await game_service.get_match_page_data(db, match_id, current_user.id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    if players is None:
        raise HTTPException(status_code=403, detail="Not a player in this match")

    lang = detect_language(request, current_user)
    return templates.TemplateResponse(
        request,
        "match.html",
        {
            "user": current_user,
            "match_id": str(match.id),
            "match_status": match.status.value,
            "players": players,
            "lang": lang,
            "_": get_translator(lang),
            "i18n": TRANSLATIONS[lang],
        },
    )
