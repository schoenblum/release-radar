"""ORM models. Importing this package registers every table and the save hooks."""

# Registered here so that no save, anywhere, can skip the audit log or the rules.
from app import record_events  # noqa: F401
from app.models.audit import AuditLog
from app.models.custom_field import CoreFieldConfig, CustomField
from app.models.institution import Institution
from app.models.lists import (
    ReleaseType,
    ResearchField,
    Unit,
    Vocabulary,
    VocabularyItem,
    Writer,
)
from app.models.release import Checkpoint, Measure, Reading, Release
from app.models.researcher import Researcher
from app.models.system import ImportRun, JobRun, RateLimitHit
from app.models.user import PasswordResetToken, RefreshToken, User, UserRole

__all__ = [
    "AuditLog",
    "Checkpoint",
    "CoreFieldConfig",
    "CustomField",
    "Institution",
    "ImportRun",
    "JobRun",
    "Measure",
    "PasswordResetToken",
    "RateLimitHit",
    "Reading",
    "RefreshToken",
    "Release",
    "ReleaseType",
    "ResearchField",
    "Researcher",
    "Unit",
    "User",
    "UserRole",
    "Vocabulary",
    "VocabularyItem",
    "Writer",
]
