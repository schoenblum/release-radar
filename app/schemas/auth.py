"""Request and response bodies for the auth endpoints.

Password rules live in ``validate_new_password``, not here, so a rejected
password produces a translatable error code. These fields only cap the size.
"""

from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserOut

MAX_PASSWORD_INPUT = 1024


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_INPUT)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 - the token scheme, not a secret
    expires_in: int
    user: UserOut


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=MAX_PASSWORD_INPUT)
    new_password: str = Field(min_length=1, max_length=MAX_PASSWORD_INPUT)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    # Tells the page whether to say "check your email" or "ask an admin". It
    # describes this install, not the address entered, so it reveals no accounts.
    email_enabled: bool


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=1, max_length=MAX_PASSWORD_INPUT)
