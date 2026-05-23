import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


async def search_players(
    db: AsyncSession,
    q: str,
    page: int,
    limit: int,
    exclude_user_id: uuid.UUID,
) -> dict:
    q = q.strip()
    offset = (page - 1) * limit

    base = select(User).where(User.id != exclude_user_id)
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
