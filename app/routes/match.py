import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import aliased

from app.deps import get_db, get_current_user
from app.i18n import TRANSLATIONS, detect_language, get_translator
from app.models import User, Match, MatchPlayer, MatchStatus
from app.templating import templates
from app.ws.manager import manager

router = APIRouter()


@router.get("/match/ongoing")
async def get_ongoing_matches(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    OtherMP = aliased(MatchPlayer)

    result = await db.execute(
        select(Match, OtherMP.user_id)
        .join(
            MatchPlayer,
            (MatchPlayer.match_id == Match.id) & (MatchPlayer.user_id == current_user.id),
        )
        .join(
            OtherMP,
            (OtherMP.match_id == Match.id) & (OtherMP.user_id != current_user.id),
        )
        .where(Match.status.in_([MatchStatus.waiting, MatchStatus.active]))
        .order_by(Match.created_at.desc())
    )

    rows = result.all()
    ongoing_by_user: dict[str, str] = {}
    for match, other_user_id in rows:
        ongoing_by_user.setdefault(str(other_user_id), str(match.id))

    return {"matches": ongoing_by_user}


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

    result = await db.execute(select(User).where(User.id == target_id))
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check for an existing waiting or active match between the two players
    my_match_ids = select(MatchPlayer.match_id).where(MatchPlayer.user_id == current_user.id)
    their_match_ids = select(MatchPlayer.match_id).where(MatchPlayer.user_id == target_id)

    result = await db.execute(
        select(Match).where(
            Match.id.in_(my_match_ids),
            Match.id.in_(their_match_ids),
            Match.status.in_([MatchStatus.waiting, MatchStatus.active]),
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return JSONResponse({
            "match_id": str(existing.id),
            "existing": True,
            "from_user_id": str(existing.inviter_id) if existing.inviter_id else None,
        })

    # Create a new match in waiting status
    match = Match(inviter_id=current_user.id)
    db.add(match)
    await db.flush()

    db.add(MatchPlayer(match_id=match.id, user_id=current_user.id, read_at=datetime.now(timezone.utc)))
    db.add(MatchPlayer(match_id=match.id, user_id=target_id))
    await db.commit()

    # Push invite event to the target wherever they are connected.
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
    result = await db.execute(
        select(MatchPlayer)
        .join(Match, Match.id == MatchPlayer.match_id)
        .where(
            MatchPlayer.match_id == match_id,
            MatchPlayer.user_id == current_user.id,
            Match.status == MatchStatus.waiting,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Invite not found")

    await db.execute(
        update(MatchPlayer)
        .where(MatchPlayer.match_id == match_id, MatchPlayer.user_id == current_user.id)
        .values(read_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return JSONResponse({"ok": True})


@router.get("/match/{match_id}")
async def match_page(
    match_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    result = await db.execute(
        select(MatchPlayer).where(
            MatchPlayer.match_id == match_id,
            MatchPlayer.user_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a player in this match")

    result = await db.execute(
        select(User)
        .join(MatchPlayer, MatchPlayer.user_id == User.id)
        .where(MatchPlayer.match_id == match_id)
    )
    players = [
        {"user_id": str(u.id), "username": u.username, "avatar_url": u.avatar_url}
        for u in result.scalars().all()
    ]

    lang = detect_language(request, current_user)
    return templates.TemplateResponse(
        request,
        "match.html",
        {
            "user": current_user,
            "match_id": str(match.id),
            "players": players,
            "lang": lang,
            "_": get_translator(lang),
            "i18n": TRANSLATIONS[lang],
        },
    )
