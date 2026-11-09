"""Researcher feedback (BRIEF §6.7, R11.1): survey templates with versions, their items with
stable keys, and the responses, with answers by item key.

Built in Phase 2 for the legacy Microsoft Forms responses (R8.1.2). The public survey page
comes in Phase 5 and adds responses with the source ``survey``. Editing a template's items makes
a new version; a response keeps the version it answered, and trends map across versions by item
key.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import Record

SOURCE_LEGACY = "legacy_import"
SOURCE_SURVEY = "survey"


class SurveyTemplate(Record, Base):
    __tablename__ = "survey_templates"
    __table_args__ = (
        UniqueConstraint("institution_id", "key", "version", name="uq_survey_templates_version"),
    )

    # The same key across versions, such as "nu_forms_2025".
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ja: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # The version new invitations use (Phase 5). A legacy template is never active.
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class SurveyItem(Record, Base):
    """One answerable thing: a box to tick, a statement on the 1–5 scale, or a text."""

    __tablename__ = "survey_items"
    __table_args__ = (
        UniqueConstraint("template_id", "key", name="uq_survey_items_key"),
        CheckConstraint("kind IN ('flag', 'scale', 'text')", name="kind_known"),
    )

    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("survey_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Stable across versions: inq_media, act_collab, sat_accuracy, comments (R11.1).
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    # The question the item belongs to: inquiries, activities, satisfaction, comments.
    question: Mapped[str] = mapped_column(String(32), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    # "None": ticking it excludes the others, and tells "nothing happened" from "skipped".
    exclusive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Interest from outside the institution (D29), reported on its own.
    external: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    label_en: Mapped[str] = mapped_column(Text, nullable=False)
    label_ja: Mapped[str | None] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class SurveyResponse(Record, Base):
    """One researcher's answers about one release.

    ``answers`` holds every item of each question that was answered: ``true``/``false`` for
    boxes, 1–5 for statements, text for comments. A question with no key in it was skipped,
    which is *missing*, never 0.
    """

    __tablename__ = "survey_responses"
    __table_args__ = (
        # A re-run of an import finds a response again by the source's own ID.
        UniqueConstraint(
            "institution_id", "source", "external_id", name="uq_survey_responses_external"
        ),
        CheckConstraint("source IN ('legacy_import', 'survey')", name="source_known"),
    )
    __audit_expand__ = frozenset({"answers"})

    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("survey_templates.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    release_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("releases.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    # The Forms export's Id column for legacy responses.
    external_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    language: Mapped[str | None] = mapped_column(String(8), nullable=True)
    # Personal: shown to office users in the record only, never on guest pages (R8.1.2).
    respondent_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    answers: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Free text written in an "other" box, by question. Maps to no item key (R8.1.2).
    other_texts: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
