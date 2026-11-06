"""Signed-in sessions: a short-lived access token plus a refresh cookie (R3.3.5).

The refresh token is a long random value kept in an httpOnly cookie, stored only
as a hash. It is not rotated on use: all tabs share one cookie, and rotation
would make tabs that refresh together sign each other out. Instead each use
extends its expiry, so sessions last through the working day and end after a
period of inactivity. One person may hold several sessions (R3.3.1).
"""

from datetime import UTC, datetime, timedelta

from fastapi import Response
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.user import RefreshToken, User
from app.services.security import generate_token, hash_token

REFRESH_COOKIE = "rr_refresh"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def _lifetime() -> timedelta:
    return timedelta(days=get_settings().REFRESH_TOKEN_EXPIRE_DAYS)


def set_refresh_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=raw_token,
        max_age=int(_lifetime().total_seconds()),
        httponly=True,
        secure=get_settings().cookie_secure,
        samesite="strict",
        path=REFRESH_COOKIE_PATH,
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE,
        httponly=True,
        secure=get_settings().cookie_secure,
        samesite="strict",
        path=REFRESH_COOKIE_PATH,
    )


async def create_session(db: AsyncSession, user: User) -> str:
    """Add a session row and return the raw token for the cookie. The caller commits."""
    raw_token = generate_token()
    db.add(
        RefreshToken(
            institution_id=user.institution_id,
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=datetime.now(UTC) + _lifetime(),
        )
    )
    await db.flush()
    return raw_token


async def find_active_session(db: AsyncSession, raw_token: str) -> RefreshToken | None:
    return await db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_token(raw_token),
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(UTC),
        )
    )


def extend_session(session: RefreshToken) -> None:
    now = datetime.now(UTC)
    session.last_used_at = now
    session.expires_at = now + _lifetime()


async def revoke_session(db: AsyncSession, raw_token: str) -> None:
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == hash_token(raw_token), RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )


async def revoke_all_sessions(db: AsyncSession, user: User) -> None:
    """End every session of a user. Access tokens stop working at once as well."""
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    user.token_version += 1
