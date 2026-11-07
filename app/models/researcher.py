"""Researchers (BRIEF section 6.3).

Identity is the ID, never the name: identical names exist (R6.3.1). Name, gender and
email-like identifiers are personal data, so tests and fixtures use synthetic values.
"""

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import FieldVersioned, Record


class Researcher(Record, FieldVersioned, Base):
    __tablename__ = "researchers"
    # The moves it lists reach the audit log one by one.
    __audit_exclude__ = frozenset({"merge_details"})
    __table_args__ = (
        CheckConstraint("gender IN ('M', 'F', 'other', 'not_recorded')", name="gender_known"),
        CheckConstraint("status IN ('incomplete', 'unverified', 'verified')", name="status_known"),
    )

    # As entered. Required, and not unique.
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    given_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    family_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name_ja: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("units.id", ondelete="RESTRICT"), nullable=True
    )
    gender: Mapped[str] = mapped_column(String(16), nullable=False, default="not_recorded")
    researchmap_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    orcid: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="incomplete")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # A merged record stays as a pointer to the survivor, so older history still
    # resolves to a person (R6.3.2).
    merged_into_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("researchers.id", ondelete="RESTRICT"), nullable=True
    )
    # What a merge did, so it can be undone: {"release_ids": [...], "filled": {field: value}}.
    merge_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
