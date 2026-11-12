"""User accounts: administration by admins, and each person's own preferences.

There is deliberately no delete route: users are deactivated, never deleted
(R3.4.1, D12). The Settings → Users page arrives in step 1.3.
"""

import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.deps import get_authenticated_user, require_admin
from app.models.user import User, UserRole
from app.routers.auth import current_user_out
from app.schemas.user import (
    CurrentUserOut,
    PasswordResetByAdmin,
    UserAdminUpdate,
    UserCreate,
    UserCreated,
    UserOut,
    UserSelfUpdate,
)
from app.services import sessions
from app.services.email import send_welcome_email
from app.services.security import generate_temporary_password, hash_password

router = APIRouter(prefix="/users", tags=["users"])


def _login_url() -> str:
    return f"{get_settings().BASE_URL.rstrip('/')}/login"


async def _get_user_in_institution(db: AsyncSession, user_id: UUID, actor: User) -> User:
    user = await db.get(User, user_id)
    if user is None or user.institution_id != actor.institution_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="user_not_found")
    return user


async def _email_taken(db: AsyncSession, actor: User, email: str) -> bool:
    existing = await db.scalar(
        select(User.id).where(User.institution_id == actor.institution_id, User.email == email)
    )
    return existing is not None


# Registered before /{user_id}, which would otherwise capture the word "me".
@router.patch("/me", response_model=CurrentUserOut)
async def update_me(
    payload: UserSelfUpdate,
    user: User = Depends(get_authenticated_user),
    db: AsyncSession = Depends(get_db),
) -> CurrentUserOut:
    """Own name, language and preferences. The language toggle also calls this at first
    sign-in. Preferences merge: a page saves only its own, and the others stay as they are."""
    changes = payload.model_dump(exclude_unset=True)
    if "preferences" in changes:
        sent = payload.preferences.model_dump(exclude_unset=True) if payload.preferences else {}
        changes["preferences"] = {**(user.preferences or {}), **sent}
    for field, value in changes.items():
        setattr(user, field, value)
    if changes:
        await db.commit()
    return await current_user_out(db, user)


@router.get("", response_model=list[UserOut])
async def list_users(
    admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)
) -> list[User]:
    users = await db.scalars(
        select(User).where(User.institution_id == admin.institution_id).order_by(User.email)
    )
    return list(users)


@router.post("", response_model=UserCreated, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserCreated:
    """Create an account and email the temporary password.

    The send is awaited, so ``email_sent`` reports what really happened. Only if
    it failed does the response carry the password for the admin to pass on.
    """
    email = payload.email.lower()
    if await _email_taken(db, admin, email):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="email_in_use")
    temporary = generate_temporary_password()
    user = User(
        institution_id=admin.institution_id,
        email=email,
        full_name=payload.full_name,
        role=payload.role,
        language=payload.language,
        password_hash=await asyncio.to_thread(hash_password, temporary),
        force_password_change=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    sent = await send_welcome_email(user.email, user.language, temporary, _login_url())
    return UserCreated(
        user=UserOut.model_validate(user),
        email_sent=sent,
        initial_password=None if sent else temporary,
    )


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: UUID,
    payload: UserAdminUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await _get_user_in_institution(db, user_id, admin)
    changes = payload.model_dump(exclude_unset=True)

    if user.id == admin.id:
        if changes.get("is_active") is False:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="cannot_deactivate_self")
        if "role" in changes and changes["role"] != UserRole.admin:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="cannot_demote_self")

    if changes.get("email") is not None:
        changes["email"] = changes["email"].lower()
        if changes["email"] != user.email and await _email_taken(db, admin, changes["email"]):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="email_in_use")

    # These columns cannot hold null. Null in the request means "leave as it is".
    for required in ("email", "role", "is_active"):
        if changes.get(required, ...) is None:
            del changes[required]

    if changes.get("is_active") is False and user.is_active:
        await sessions.revoke_all_sessions(db, user)
    for field, value in changes.items():
        setattr(user, field, value)
    await db.commit()
    return user


@router.post("/{user_id}/reset-password", response_model=PasswordResetByAdmin)
async def reset_password_by_admin(
    user_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> PasswordResetByAdmin:
    """Issue a new temporary password and sign the person out everywhere."""
    user = await _get_user_in_institution(db, user_id, admin)
    if user.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="use_change_password")
    temporary = generate_temporary_password()
    user.password_hash = await asyncio.to_thread(hash_password, temporary)
    user.force_password_change = True
    await sessions.revoke_all_sessions(db, user)
    await db.commit()

    sent = await send_welcome_email(user.email, user.language, temporary, _login_url())
    return PasswordResetByAdmin(email_sent=sent, initial_password=None if sent else temporary)
