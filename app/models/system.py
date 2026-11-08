"""Operational tables: scheduled-job history, import history and rate-limit counters."""

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
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import InstitutionScoped


class JobRun(InstitutionScoped, Base):
    """One execution of a scheduled job.

    The unique constraint is the durable half of single-firing: a worker that
    reaches a slot after another has finished it still cannot run it again.
    The status gives every job a visible outcome, including "skipped" with the
    reason, so nothing fails silently.
    """

    __tablename__ = "job_runs"
    __table_args__ = (
        UniqueConstraint("institution_id", "job_key", "slot", name="uq_job_runs_slot"),
        CheckConstraint(
            "status IN ('running', 'succeeded', 'skipped', 'failed')", name="status_known"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    slot: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    worker: Mapped[str | None] = mapped_column(String(128), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ImportRun(InstitutionScoped, Base):
    """One check or import of the old workbook (step 1.8), with its report.

    The report is kept as entries, not as text, so it can be read later in either language.
    The files themselves are not kept: once imported, the data lives in Release Radar.
    """

    __tablename__ = "import_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    committed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    file_names: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    counts: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    entries: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RateLimitHit(InstitutionScoped, Base):
    """A fixed-window counter shared by all workers.

    ``bucket`` is a SHA-256 hash, so client addresses and email addresses are
    not stored in this table.
    """

    __tablename__ = "rate_limit_hits"
    __table_args__ = (
        UniqueConstraint("institution_id", "bucket", "window_start", name="uq_rate_limit_window"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bucket: Mapped[str] = mapped_column(String(64), nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
