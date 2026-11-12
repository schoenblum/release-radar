"""ORM models. Importing this package registers every table and the save hooks."""

# Registered here so that no save, anywhere, can skip the audit log or the rules.
from app import record_events  # noqa: F401
from app.models.audit import AuditLog
from app.models.custom_field import CoreFieldConfig, CustomField
from app.models.institution import Institution
from app.models.integration import Integration
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
from app.models.score_profile import ScoreProfile, ScoreProfileVersion
from app.models.survey import SurveyItem, SurveyResponse, SurveyTemplate
from app.models.system import ImportRun, JobRun, RateLimitHit
from app.models.user import PasswordResetToken, RefreshToken, User, UserRole

__all__ = [
    "AuditLog",
    "Checkpoint",
    "CoreFieldConfig",
    "CustomField",
    "Institution",
    "ImportRun",
    "Integration",
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
    "ScoreProfile",
    "ScoreProfileVersion",
    "SurveyItem",
    "SurveyResponse",
    "SurveyTemplate",
    "Unit",
    "User",
    "UserRole",
    "Vocabulary",
    "VocabularyItem",
    "Writer",
]
