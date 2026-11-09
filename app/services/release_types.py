"""What kind of release a new one is (R6.4.1)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Institution, ReleaseType


async def default_release_type_id(db: AsyncSession, institution: Institution) -> UUID | None:
    """The institution's default, unless an admin has retired that type since."""
    if institution.default_release_type_id is None:
        return None
    return await db.scalar(
        select(ReleaseType.id).where(
            ReleaseType.id == institution.default_release_type_id,
            ReleaseType.is_active.is_(True),
        )
    )
