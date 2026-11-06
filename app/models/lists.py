"""The lists that releases refer to (BRIEF section 6.2). Names exist in EN and JA (R5.4.3)."""

import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import Record


class ResearchField(Record, Base):
    """A field such as STEM or HSS. The brief calls this ``Field``."""

    __tablename__ = "research_fields"
    __table_args__ = (
        UniqueConstraint("institution_id", "name_en", name="uq_research_fields_name"),
    )

    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ja: Mapped[str | None] = mapped_column(String(255), nullable=True)
    scope_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Unit(Record, Base):
    """A school, institute or center."""

    __tablename__ = "units"
    __table_args__ = (
        UniqueConstraint("institution_id", "key", name="uq_units_key"),
        CheckConstraint(
            "unit_type IN ('school', 'institute', 'center', 'other')", name="unit_type_known"
        ),
    )

    # The value used in the source workbook.
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ja: Mapped[str | None] = mapped_column(String(255), nullable=True)
    short_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    unit_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    aliases: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    default_field_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_fields.id", ondelete="RESTRICT"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Writer(Record, Base):
    """A list entry, not a user: former staff stay as writers (R3.2.1)."""

    __tablename__ = "writers"
    __table_args__ = (UniqueConstraint("institution_id", "user_id", name="uq_writers_user"),)

    display_name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name_ja: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )


class Vocabulary(Record, Base):
    """A named list for select-type custom fields."""

    __tablename__ = "vocabularies"
    __table_args__ = (UniqueConstraint("institution_id", "key", name="uq_vocabularies_key"),)

    key: Mapped[str] = mapped_column(String(64), nullable=False)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ja: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class VocabularyItem(Record, Base):
    __tablename__ = "vocabulary_items"
    __table_args__ = (UniqueConstraint("vocabulary_id", "key", name="uq_vocabulary_items_key"),)

    vocabulary_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vocabularies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # What custom values store, so a label can change without touching them.
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    label_en: Mapped[str] = mapped_column(String(255), nullable=False)
    label_ja: Mapped[str | None] = mapped_column(String(255), nullable=True)
    aliases: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
