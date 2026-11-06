"""The audit log: every change to a record (R3.4.4, R6.3.2).

Rows are written by ``app.services.audit`` and never changed. There is no foreign key
to the entity, so the history of a record outlives the record itself.
"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import InstitutionScoped, UuidKeyed


class AuditLog(UuidKeyed, InstitutionScoped, Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        CheckConstraint("action IN ('create', 'update', 'delete')", name="action_known"),
        Index("ix_audit_log_entity", "institution_id", "entity_type", "entity_id", "created_at"),
    )

    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String(8), nullable=False)
    # Null for "create" and "delete", which carry a snapshot instead.
    field: Mapped[str | None] = mapped_column(String(128), nullable=True)
    old_value: Mapped[object | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    new_value: Mapped[object | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    # Null means the system, such as a rule or a scheduled job.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    # Why, where that is not obvious from the change: an import, a legacy correction.
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
