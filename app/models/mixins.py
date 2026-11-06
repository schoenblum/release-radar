"""Columns shared by the tables: institution scope, timestamps, acting user."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, declared_attr, mapped_column


class InstitutionScoped:
    """Scopes a row to one institution (R5.2.1)."""

    @declared_attr
    def institution_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(
            UUID(as_uuid=True),
            ForeignKey("institutions.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ActorTracked:
    """Who created and last changed a row. RESTRICT keeps users undeletable (R3.4.2)."""

    @declared_attr
    def created_by_id(cls) -> Mapped[uuid.UUID | None]:
        return mapped_column(
            UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
        )

    @declared_attr
    def updated_by_id(cls) -> Mapped[uuid.UUID | None]:
        return mapped_column(
            UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
        )
