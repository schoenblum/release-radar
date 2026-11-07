"""Access to the single institution row of this install (R5.2.1)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.institution import Institution
from app.models.lists import Writer
from app.models.release import Release
from app.models.user import User


async def get_institution(db: AsyncSession) -> Institution:
    """Return the institution. ``app.bootstrap`` creates it before the app starts."""
    institution = await db.scalar(select(Institution).order_by(Institution.created_at).limit(1))
    if institution is None:
        raise RuntimeError("No institution row found. Run: python -m app.bootstrap")
    return institution


async def landing_for(db: AsyncSession, user: User) -> str:
    """The view this person lands on. "Mine" only once there is something of theirs to see."""
    institution = await db.get(Institution, user.institution_id)
    landing = institution.landing_pages.get(user.role.value, "all")
    if landing == "mine":
        theirs = await db.scalar(
            select(Release.id)
            .join(Writer, Writer.id == Release.writer_id)
            .where(
                Writer.user_id == user.id,
                Release.institution_id == user.institution_id,
                Release.deleted_at.is_(None),
            )
            .limit(1)
        )
        if theirs is None:
            return "all"
    return landing
