"""Shared FastAPI dependencies: the signed-in user and role guards."""

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User, UserRole
from app.services.security import decode_access_token

_bearer = HTTPBearer(auto_error=False)


async def get_authenticated_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Any valid session, including one that still has to change its password."""
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid_token")
    try:
        user_id = UUID(payload["sub"])
    except (ValueError, TypeError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid_token") from exc
    user = await db.get(User, user_id)
    if user is None or not user.is_active or payload["tv"] != user.token_version:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid_token")
    return user


async def get_current_user(user: User = Depends(get_authenticated_user)) -> User:
    """A signed-in user who has finished the forced password change."""
    if user.force_password_change:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="password_change_required")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="admin_required")
    return user
