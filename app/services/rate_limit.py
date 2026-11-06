"""Fixed-window rate limiting kept in Postgres, so all workers share the counts.

The Media Monitor did this in nginx. Release Radar has no nginx, and the limits
must work the same way on the Mac mini and on the NAS (BRIEF section 5.5).
"""

import hashlib
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system import RateLimitHit


def _bucket(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _window_start(window_seconds: int, now: datetime | None = None) -> datetime:
    timestamp = (now or datetime.now(UTC)).timestamp()
    return datetime.fromtimestamp(timestamp // window_seconds * window_seconds, tz=UTC)


async def current_count(
    db: AsyncSession, institution_id: UUID, key: str, window_seconds: int
) -> int:
    count = await db.scalar(
        select(RateLimitHit.count).where(
            RateLimitHit.institution_id == institution_id,
            RateLimitHit.bucket == _bucket(key),
            RateLimitHit.window_start == _window_start(window_seconds),
        )
    )
    return count or 0


async def record_hit(db: AsyncSession, institution_id: UUID, key: str, window_seconds: int) -> int:
    """Add one to the counter, commit at once and return the new count.

    The commit means a hit still counts when the request then fails.
    """
    statement = insert(RateLimitHit).values(
        institution_id=institution_id,
        bucket=_bucket(key),
        window_start=_window_start(window_seconds),
        count=1,
    )
    statement = statement.on_conflict_do_update(
        constraint="uq_rate_limit_window",
        set_={"count": RateLimitHit.count + 1},
    ).returning(RateLimitHit.count)
    count = await db.scalar(statement)
    await db.commit()
    return count or 0


def too_many_requests(window_seconds: int) -> HTTPException:
    now = datetime.now(UTC).timestamp()
    retry_after = int(window_seconds - now % window_seconds) + 1
    return HTTPException(
        status.HTTP_429_TOO_MANY_REQUESTS,
        detail="rate_limited",
        headers={"Retry-After": str(retry_after)},
    )


async def delete_expired_hits(db: AsyncSession, *, older_than: datetime) -> int:
    """Housekeeping. The caller commits."""
    result = await db.execute(delete(RateLimitHit).where(RateLimitHit.window_start < older_than))
    return result.rowcount
