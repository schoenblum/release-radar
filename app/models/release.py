"""Releases, and the measures read from them at each checkpoint (BRIEF sections 6.4, 6.5).

D2: one mechanism for automatic and manual data, reminders, missing states and timing:
readings per measure and checkpoint rather than fixed columns.
"""

import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import FieldVersioned, Record


class Release(Record, FieldVersioned, Base):
    __tablename__ = "releases"
    __table_args__ = (
        # Postgres lets several drafts have no code yet.
        UniqueConstraint("institution_id", "code", name="uq_releases_code"),
        # R7.5.6: a release needs a title or a DOI.
        CheckConstraint("title IS NOT NULL OR doi IS NOT NULL", name="title_or_doi"),
        CheckConstraint(
            "ea_top_position IS NULL OR (ea_top_page AND ea_top_position >= 1)",
            name="ea_top_position_valid",
        ),
        Index("ix_releases_institution_release_date", "institution_id", "release_date"),
    )
    # Recorded per custom field, as custom_values.<key>.
    __audit_expand__ = frozenset({"custom_values"})

    # Null while a draft has no release date, because the number comes from the academic
    # year of that date. Assigned once, then immutable.
    code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    title_ja: Mapped[str | None] = mapped_column(Text, nullable=True)
    writer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("writers.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    # The one corresponding researcher (D5).
    researcher_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("researchers.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    also_featured: Mapped[str | None] = mapped_column(Text, nullable=True)
    # A snapshot at release time: researchers move (D7).
    unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("units.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    field_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_fields.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    doi: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    journal: Mapped[str | None] = mapped_column(Text, nullable=True)
    paper_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    publication_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    authors: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    embargoed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    release_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # US Eastern time, as EurekAlert works in it. Not converted.
    release_time_et: Mapped[time | None] = mapped_column(Time, nullable=True)
    ea_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    website_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    ea_top_page: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # 1 is the top spot.
    ea_top_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Institution and personal custom fields, by field key (section 6.6). A value is
    # {"state": "value", "value": ...}, an explicit N/A is {"state": "not_applicable"},
    # and a key that is absent is missing. Reassign the dict to change it.
    custom_values: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class Checkpoint(Record, Base):
    """A point in time relative to the release date (D3)."""

    __tablename__ = "checkpoints"
    __table_args__ = (
        UniqueConstraint("institution_id", "key", name="uq_checkpoints_key"),
        CheckConstraint("offset_days >= 0", name="offset_not_negative"),
    )

    key: Mapped[str] = mapped_column(String(32), nullable=False)
    label_en: Mapped[str] = mapped_column(String(255), nullable=False)
    label_ja: Mapped[str | None] = mapped_column(String(255), nullable=True)
    offset_days: Mapped[int] = mapped_column(Integer, nullable=False)


class Measure(Record, Base):
    """A metric at a checkpoint, such as ``altmetric.d28``."""

    __tablename__ = "measures"
    __table_args__ = (
        UniqueConstraint("institution_id", "key", name="uq_measures_key"),
        CheckConstraint(
            "applicability IN "
            "('always', 'embargoed', 'has_doi', 'has_ea_url', 'website_on_domain')",
            name="applicability_known",
        ),
    )

    key: Mapped[str] = mapped_column(String(64), nullable=False)
    metric: Mapped[str] = mapped_column(String(64), nullable=False)
    # Null for counts that do not belong to a checkpoint, such as pickups.
    checkpoint_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("checkpoints.id", ondelete="RESTRICT"), nullable=True
    )
    # manual, ga4, altmetric_api, derived, and more as phases arrive.
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    applicability: Mapped[str] = mapped_column(String(32), nullable=False, default="always")
    unit: Mapped[str] = mapped_column(String(16), nullable=False)
    label_en: Mapped[str] = mapped_column(String(255), nullable=False)
    label_ja: Mapped[str | None] = mapped_column(String(255), nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Releases dated earlier get not applicable (R6.7.1, D26).
    collected_from: Mapped[date | None] = mapped_column(Date, nullable=True)


class Reading(Record, Base):
    """One measure of one release. See ``app.services.readings`` for how states change."""

    __tablename__ = "readings"
    __table_args__ = (
        UniqueConstraint("release_id", "measure_id", name="uq_readings_release_measure"),
        CheckConstraint("state IN ('value', 'not_applicable', 'missing')", name="state_known"),
        CheckConstraint("source IN ('manual', 'auto')", name="source_known"),
        # A number and the state "value" always go together, so nothing can store a 0
        # or any other stand-in for "unknown".
        CheckConstraint("(state = 'value') = (value IS NOT NULL)", name="value_matches_state"),
        CheckConstraint("value >= 0", name="value_not_negative"),
    )

    release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("releases.id", ondelete="CASCADE"), nullable=False
    )
    measure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("measures.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="missing")
    # "auto" on a not_applicable reading means a rule set it, and a rule may undo it.
    # "manual" means a person did, and it stays.
    source: Mapped[str] = mapped_column(String(8), nullable=False, default="auto")
    # Kept for the audit trail only: there is no "late" state (R6.5.2).
    entered_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    entered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # For optimistic concurrency (R3.3.3): a reading holds a single value.
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Declared so a new release and its readings are written in the right order. Never
    # lazy-loaded, because that fails silently-late under async.
    release: Mapped[Release] = relationship(lazy="raise")
    measure: Mapped[Measure] = relationship(lazy="raise")
