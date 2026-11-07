"""Request and response bodies for user accounts."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole

Language = Literal["en", "ja"]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str | None
    role: UserRole
    language: Language | None
    is_active: bool
    force_password_change: bool
    last_login_at: datetime | None
    created_at: datetime


class DataColumns(BaseModel):
    """Differences from the default columns, so a column added later still shows up."""

    hidden: list[str] = Field(default=[], max_length=500)
    shown: list[str] = Field(default=[], max_length=500)


class UserPreferences(BaseModel):
    data_columns: DataColumns = DataColumns()


class CurrentUserOut(UserOut):
    """The signed-in person, with where they land after signing in."""

    landing: str = "all"
    preferences: UserPreferences = UserPreferences()


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=255)
    role: UserRole = UserRole.editor
    language: Language | None = None


class UserCreated(BaseModel):
    user: UserOut
    email_sent: bool
    # Present only when the email could not be sent, so the admin can pass it on.
    initial_password: str | None = None


class UserAdminUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, max_length=255)
    role: UserRole | None = None
    language: Language | None = None
    is_active: bool | None = None


class UserSelfUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    language: Language | None = None
    preferences: UserPreferences | None = None


class PasswordResetByAdmin(BaseModel):
    email_sent: bool
    initial_password: str | None = None
