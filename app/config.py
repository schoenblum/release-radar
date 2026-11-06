"""Application configuration, loaded from environment variables or ``.env``."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENVIRONMENT: Literal["development", "test", "production"] = "development"
    # Public address of the app. Used in email links and to decide whether the
    # session cookie is marked Secure.
    BASE_URL: str = "http://localhost:8000"

    DATABASE_URL: str

    SECRET_KEY: str = Field(min_length=32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    # Sliding: every refresh extends the session, so nobody is signed out during
    # a working day (R3.3.5). An idle session ends after this many days.
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    PASSWORD_RESET_EXPIRE_MINUTES: int = 60
    BCRYPT_ROUNDS: int = 12

    FERNET_KEY: str
    # Optional comma-separated older keys, kept readable during a key rotation.
    FERNET_KEYS: str | None = None

    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_SECURITY: Literal["starttls", "ssl", "none"] = "starttls"
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str | None = None

    # Used once, when the database has no admin yet.
    BOOTSTRAP_ADMIN_EMAIL: str | None = None
    BOOTSTRAP_ADMIN_PASSWORD: str | None = None

    # Used once, when the institution row is first created. Editable afterwards
    # in Settings.
    INSTITUTION_NAME_EN: str = "My institution"
    INSTITUTION_NAME_JA: str | None = None
    INSTITUTION_TIMEZONE: str = "Asia/Tokyo"
    INSTITUTION_WEBSITE_DOMAIN: str | None = None
    INSTITUTION_CONTACT_EMAIL: str | None = None

    BRAND_PACK_PATH: str = "/brand"

    # Without a passphrase the backup job records a visible "skipped" status
    # rather than writing an unencrypted dump.
    BACKUP_PASSPHRASE: str | None = None
    BACKUP_DIR: str = "/backups"
    BACKUP_RETENTION_DAYS: int = 14
    BACKUP_HOUR: int = Field(default=3, ge=0, le=23)

    SCHEDULER_ENABLED: bool = True
    # A positive value registers a no-op job at this interval, used only to
    # verify single-firing after a deploy (see HANDOVER section 9).
    SCHEDULER_TEST_INTERVAL_SECONDS: int = Field(default=0, ge=0)

    @property
    def cookie_secure(self) -> bool:
        return self.BASE_URL.lower().startswith("https://")

    @property
    def smtp_configured(self) -> bool:
        return bool(self.SMTP_HOST and self.SMTP_FROM)

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
