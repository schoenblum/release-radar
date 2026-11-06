"""Sign-in, sessions and passwords."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.deps import get_authenticated_user
from app.models.user import PasswordResetToken, User
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from app.schemas.user import UserOut
from app.services import audit, rate_limit, sessions
from app.services.email import send_password_reset_email
from app.services.institution import get_institution
from app.services.security import (
    create_access_token,
    dummy_password_hash,
    generate_token,
    hash_password,
    hash_token,
    validate_new_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)

LOGIN_WINDOW_SECONDS = 15 * 60
# Failed attempts per window. Offices share one address, so the per-address
# limit is high and the tight limit applies to an address and account together.
LOGIN_MAX_FAILURES_PAIR = 10
LOGIN_MAX_FAILURES_ADDRESS = 100
FORGOT_WINDOW_SECONDS = 60 * 60
FORGOT_MAX_PER_ADDRESS = 20
FORGOT_MAX_PER_ACCOUNT = 3
RESET_WINDOW_SECONDS = 15 * 60
RESET_MAX_PER_ADDRESS = 20


def _client_address(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _token_response(user: User) -> TokenResponse:
    token, expires_in = create_access_token(user.id, user.token_version)
    return TokenResponse(
        access_token=token, expires_in=expires_in, user=UserOut.model_validate(user)
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    institution = await get_institution(db)
    email = payload.email.lower()
    address = _client_address(request)
    pair_key = f"login:pair:{address}:{email}"
    address_key = f"login:address:{address}"

    pair_count = await rate_limit.current_count(db, institution.id, pair_key, LOGIN_WINDOW_SECONDS)
    address_count = await rate_limit.current_count(
        db, institution.id, address_key, LOGIN_WINDOW_SECONDS
    )
    if pair_count >= LOGIN_MAX_FAILURES_PAIR or address_count >= LOGIN_MAX_FAILURES_ADDRESS:
        raise rate_limit.too_many_requests(LOGIN_WINDOW_SECONDS)

    user = await db.scalar(
        select(User).where(User.institution_id == institution.id, User.email == email)
    )
    # Verify against a dummy hash for unknown accounts, so response time does not
    # reveal which addresses exist. bcrypt is slow, so it runs off the event loop.
    password_ok = await asyncio.to_thread(
        verify_password,
        payload.password,
        user.password_hash if user else dummy_password_hash(),
    )
    if user is None or not user.is_active or not password_ok:
        await rate_limit.record_hit(db, institution.id, pair_key, LOGIN_WINDOW_SECONDS)
        await rate_limit.record_hit(db, institution.id, address_key, LOGIN_WINDOW_SECONDS)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials")

    user.last_login_at = datetime.now(UTC)
    raw_token = await sessions.create_session(db, user)
    await db.commit()
    sessions.set_refresh_cookie(response, raw_token)
    return _token_response(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request, response: Response, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    raw_token = request.cookies.get(sessions.REFRESH_COOKIE)
    session = await sessions.find_active_session(db, raw_token) if raw_token else None
    if session is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="session_expired")
    user = await db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="session_expired")
    sessions.extend_session(session)
    await db.commit()
    sessions.set_refresh_cookie(response, raw_token)
    return _token_response(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)) -> None:
    raw_token = request.cookies.get(sessions.REFRESH_COOKIE)
    if raw_token:
        await sessions.revoke_session(db, raw_token)
        await db.commit()
    sessions.clear_refresh_cookie(response)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_authenticated_user)) -> User:
    return user


@router.post("/change-password", response_model=TokenResponse)
async def change_password(
    payload: ChangePasswordRequest,
    response: Response,
    user: User = Depends(get_authenticated_user),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Set a new password, end all other sessions and keep this one signed in."""
    current_ok = await asyncio.to_thread(
        verify_password, payload.current_password, user.password_hash
    )
    if not current_ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="current_password_incorrect")
    validate_new_password(payload.new_password, current=payload.current_password)

    user.password_hash = await asyncio.to_thread(hash_password, payload.new_password)
    user.force_password_change = False
    await sessions.revoke_all_sessions(db, user)
    raw_token = await sessions.create_session(db, user)
    await db.commit()
    sessions.set_refresh_cookie(response, raw_token)
    return _token_response(user)


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> ForgotPasswordResponse:
    """Always answers the same way, so it does not reveal which addresses exist."""
    settings = get_settings()
    institution = await get_institution(db)
    count = await rate_limit.record_hit(
        db,
        institution.id,
        f"forgot:address:{_client_address(request)}",
        FORGOT_WINDOW_SECONDS,
    )
    if count > FORGOT_MAX_PER_ADDRESS:
        raise rate_limit.too_many_requests(FORGOT_WINDOW_SECONDS)

    answer = ForgotPasswordResponse(email_enabled=settings.smtp_configured)
    if not settings.smtp_configured:
        logger.warning("Password reset requested, but SMTP is not configured")
        return answer

    email = payload.email.lower()
    # Past this limit the account's owner stops receiving mail. The answer stays
    # the same, so this limit cannot be used to find out which addresses exist.
    account_count = await rate_limit.record_hit(
        db, institution.id, f"forgot:account:{email}", FORGOT_WINDOW_SECONDS
    )
    if account_count > FORGOT_MAX_PER_ACCOUNT:
        return answer

    user = await db.scalar(
        select(User).where(User.institution_id == institution.id, User.email == email)
    )
    if user is None or not user.is_active:
        return answer

    now = datetime.now(UTC)
    # A new link replaces any earlier one.
    await db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
        .values(used_at=now)
    )
    raw_token = generate_token()
    db.add(
        PasswordResetToken(
            institution_id=user.institution_id,
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=now + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES),
        )
    )
    await db.commit()

    reset_url = f"{settings.BASE_URL.rstrip('/')}/reset-password?token={raw_token}"
    background.add_task(
        send_password_reset_email,
        to=user.email,
        language=user.language,
        reset_url=reset_url,
        expires_minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES,
    )
    return answer


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    payload: ResetPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> None:
    institution = await get_institution(db)
    count = await rate_limit.record_hit(
        db,
        institution.id,
        f"reset:address:{_client_address(request)}",
        RESET_WINDOW_SECONDS,
    )
    if count > RESET_MAX_PER_ADDRESS:
        raise rate_limit.too_many_requests(RESET_WINDOW_SECONDS)

    token = await db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == hash_token(payload.token),
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > datetime.now(UTC),
        )
    )
    user = await db.get(User, token.user_id) if token else None
    if token is None or user is None or not user.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="reset_token_invalid")

    validate_new_password(payload.new_password)
    # The link proves who this is, so the change is theirs in the audit log.
    audit.set_actor(db, user.id)
    user.password_hash = await asyncio.to_thread(hash_password, payload.new_password)
    user.force_password_change = False
    token.used_at = datetime.now(UTC)
    await sessions.revoke_all_sessions(db, user)
    await db.commit()
