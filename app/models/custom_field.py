"""Custom fields and the configuration of core fields (BRIEF section 6.6).

Custom values themselves live on ``Release.custom_values``.
"""

import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import FieldVersioned, Record


class CustomField(Record, FieldVersioned, Base):
    __tablename__ = "custom_fields"
    __table_args__ = (
        UniqueConstraint("institution_id", "key", name="uq_custom_fields_key"),
        CheckConstraint(
            "field_type IN ('integer', 'number', 'text', 'long_text', 'date', 'boolean', "
            "'single_select', 'multi_select', 'url')",
            name="field_type_known",
        ),
        CheckConstraint("scope IN ('institution', 'personal')", name="scope_known"),
        # A personal field has an owner, and only a personal field has one.
        CheckConstraint(
            "(scope = 'personal') = (owner_id IS NOT NULL)", name="owner_matches_scope"
        ),
        CheckConstraint("NOT required OR scope = 'institution'", name="required_institution_only"),
        # Personal fields never reach evaluation pages (R6.6.2).
        CheckConstraint(
            "NOT score_eligible OR (scope = 'institution' AND field_type IN ('integer', 'number'))",
            name="score_eligible_numeric_institution",
        ),
    )

    key: Mapped[str] = mapped_column(String(64), nullable=False)
    label_en: Mapped[str] = mapped_column(String(255), nullable=False)
    label_ja: Mapped[str | None] = mapped_column(String(255), nullable=True)
    help_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    help_ja: Mapped[str | None] = mapped_column(Text, nullable=True)
    field_type: Mapped[str] = mapped_column(String(16), nullable=False)
    # Options written directly on the field, unless it uses a vocabulary.
    options: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    vocabulary_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vocabularies.id", ondelete="RESTRICT"), nullable=True
    )
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # The workbook column this field is filled from by an import (Daniel, 2026-11-12): its
    # heading, so a later import of an updated workbook fills it again.
    import_heading: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Setting this creates due items (section 7.5).
    due_checkpoint_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("checkpoints.id", ondelete="RESTRICT"), nullable=True
    )
    score_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class CoreFieldConfig(Record, FieldVersioned, Base):
    """How admins have adapted a core release field: relabel, hide, require, reorder (R6.6.3)."""

    __tablename__ = "core_field_configs"
    __table_args__ = (UniqueConstraint("institution_id", "key", name="uq_core_field_configs_key"),)

    key: Mapped[str] = mapped_column(String(64), nullable=False)
    # Null keeps the translated default label.
    label_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    label_ja: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
