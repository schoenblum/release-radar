"""Score profiles (R8.2): named, weighted sets of components, one of them the default.

Every save makes a new version and old versions stay readable, so a report can cite the version
its scores came from. Versions are never changed after they are written.
"""

import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import Record

SEEDED_KEY = "news_performance"


class ScoreProfile(Record, Base):
    __tablename__ = "score_profiles"
    __table_args__ = (
        UniqueConstraint("institution_id", "key", name="uq_score_profiles_key"),
        # One default per institution.
        Index(
            "uq_score_profiles_default",
            "institution_id",
            unique=True,
            postgresql_where=text("is_default"),
        ),
    )

    # "news_performance" for the seeded profile; None for profiles admins make.
    key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # The seeded default never takes satisfaction or research outcomes (R8.2.3).
    seeded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ScoreProfileVersion(Record, Base):
    __tablename__ = "score_profile_versions"
    __table_args__ = (
        UniqueConstraint("profile_id", "version", name="uq_score_profile_versions_version"),
        CheckConstraint("altmetric_basis IN ('increase', 'd28')", name="altmetric_basis_known"),
        CheckConstraint("coverage_min BETWEEN 0 AND 100", name="coverage_min_range"),
        CheckConstraint("comparison_years BETWEEN 1 AND 10", name="comparison_years_range"),
        CheckConstraint("min_values >= 1", name="min_values_positive"),
    )

    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("score_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ja: Mapped[str | None] = mapped_column(String(255), nullable=True)
    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Component key → weight, the weights totalling 100. "altmetric" is read on the basis below.
    weights: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # increase (d28 − d0, the default, D15) or d28 (R8.2.2).
    altmetric_basis: Mapped[str] = mapped_column(String(16), nullable=False, default="increase")
    # Percent of the applicable weight that must have a value for a score (BRIEF §8.3).
    coverage_min: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    # Academic years in the comparison set: the release's own and the ones before it.
    comparison_years: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    # A component with fewer values than this in the comparison set counts as missing
    # (Daniel, 2026-11-09).
    min_values: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
