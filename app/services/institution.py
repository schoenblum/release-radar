"""Access to the single institution row of this install (R5.2.1)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.institution import Institution


async def get_institution(db: AsyncSession) -> Institution:
    """Return the institution. ``app.bootstrap`` creates it before the app starts."""
    institution = await db.scalar(select(Institution).order_by(Institution.created_at).limit(1))
    if institution is None:
        raise RuntimeError("No institution row found. Run: python -m app.bootstrap")
    return institution
