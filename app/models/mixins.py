"""Columns and behaviour shared by the tables."""

import uuid
from datetime import datetime
from typing import ClassVar

from sqlalchemy import DateTime, ForeignKey, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, declared_attr, mapped_column


class UuidKeyed:
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


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
    """Who created and last changed a row. RESTRICT keeps users undeletable (R3.4.2).

    Filled in automatically on save from the actor set by ``audit.set_actor``.
    """

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


class Audited:
    """Every change to this model goes to the audit log automatically (R3.4.4).

    A class can narrow what is recorded:
    - ``__audit_exclude__``: technical columns that are not recorded at all.
    - ``__audit_redact__``: the change is recorded, but never the value.
    - ``__audit_expand__``: JSON columns recorded per key instead of as a whole.

    Reassign a JSON column rather than changing it in place, so the change is seen.
    """

    __audit_exclude__: ClassVar[frozenset[str]] = frozenset()
    __audit_redact__: ClassVar[frozenset[str]] = frozenset()
    __audit_expand__: ClassVar[frozenset[str]] = frozenset()


class FieldVersioned:
    """A version counter per field, for per-field optimistic concurrency (R3.3.2, R3.3.3).

    Two people changing different fields never conflict. If two change the same
    field, the second save names a version that is no longer current and is refused.
    """

    field_versions: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )


class Record(UuidKeyed, InstitutionScoped, Timestamped, ActorTracked, Audited):
    """What every institution-owned record has (BRIEF section 6)."""
