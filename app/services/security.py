"""Password hashing, access tokens and random tokens."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any
from uuid import UUID

import bcrypt
import jwt
from fastapi import HTTPException, status

from app.config import get_settings

# bcrypt reads only the first 72 bytes of a password. Longer ones are refused
# rather than silently truncated. Japanese characters take three bytes each.
PASSWORD_MAX_BYTES = 72
PASSWORD_MIN_LENGTH = 10

_settings = get_settings()


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=_settings.BCRYPT_ROUNDS)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    encoded = password.encode("utf-8")
    if len(encoded) > PASSWORD_MAX_BYTES:
        return False
    return bcrypt.checkpw(encoded, password_hash.encode("ascii"))


@lru_cache
def dummy_password_hash() -> str:
    """A hash to verify against for unknown accounts, so response time does not
    reveal which email addresses are registered."""
    return hash_password(secrets.token_urlsafe(16))


def validate_new_password(password: str, *, current: str | None = None) -> None:
    """Raise an error carrying a code the frontend can translate."""
    if len(password) < PASSWORD_MIN_LENGTH:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="password_too_short")
    if len(password.encode("utf-8")) > PASSWORD_MAX_BYTES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="password_too_long")
    if current is not None and password == current:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="password_unchanged")


def create_access_token(user_id: UUID, token_version: int) -> tuple[str, int]:
    """Return a signed access token and its lifetime in seconds."""
    now = datetime.now(UTC)
    lifetime = timedelta(minutes=_settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "typ": "access",
        "tv": token_version,
        "iat": now,
        "exp": now + lifetime,
    }
    token = jwt.encode(payload, _settings.SECRET_KEY, algorithm=_settings.JWT_ALGORITHM)
    return token, int(lifetime.total_seconds())


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(
            token,
            _settings.SECRET_KEY,
            algorithms=[_settings.JWT_ALGORITHM],
            options={"require": ["exp", "sub", "typ", "tv"]},
        )
    except jwt.PyJWTError:
        return None
    return payload if payload["typ"] == "access" else None


def generate_token(num_bytes: int = 32) -> str:
    """A URL-safe random token for sessions and password resets."""
    return secrets.token_urlsafe(num_bytes)


def generate_temporary_password() -> str:
    return secrets.token_urlsafe(12)


def hash_token(token: str) -> str:
    """SHA-256 is appropriate here because the tokens are long and random."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
