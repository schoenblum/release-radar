"""In-process job scheduling with single-firing across Uvicorn workers.

Each worker starts its own APScheduler, so every job fires once per worker.
``run_job`` makes sure only one of them actually runs it, in two layers:

1. A transaction-scoped Postgres advisory lock, so workers arriving at the same
   moment do not race. The losers stop here.
2. A row in ``job_runs``, unique per job and time slot. The advisory lock ends
   with its transaction, so on its own it would let a slower worker run the slot
   again once the first had committed. The row closes that gap.

Every run leaves a visible status, including "skipped" with the reason.

Jobs live in memory and are registered from code at startup, so there is no
APScheduler table and no synchronous database driver.
"""

import hashlib
import logging
import os
import socket
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert

from app.config import get_settings
from app.database import SessionLocal
from app.models.system import JobRun
from app.models.user import PasswordResetToken, RefreshToken
from app.services.institution import get_institution
from app.services.rate_limit import delete_expired_hits

logger = logging.getLogger(__name__)

JOB_BACKUP = "backup-nightly"
JOB_BACKUP_MANUAL = "backup-manual"
JOB_HOUSEKEEPING = "housekeeping"
JOB_SCHEDULER_TEST = "scheduler-test"

# A run still marked "running" after this long lost its worker to a crash or restart.
STALE_RUN_AFTER = timedelta(hours=6)
RETAIN_JOB_RUNS_FOR = timedelta(days=365)
RETAIN_EXPIRED_TOKENS_FOR = timedelta(days=30)

_scheduler: AsyncIOScheduler | None = None


@dataclass(frozen=True)
class JobResult:
    status: Literal["succeeded", "skipped", "failed"] = "succeeded"
    detail: str | None = None


JobFunction = Callable[[], Awaitable[JobResult | None]]


def _worker_name() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"[:128]


def _lock_key(payload: str) -> int:
    """Map a string to a positive 63-bit integer for ``pg_try_advisory_xact_lock``."""
    digest = hashlib.sha256(payload.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") & 0x7FFF_FFFF_FFFF_FFFF


def current_slot(slot_seconds: int, now: datetime | None = None) -> datetime:
    """The start of the time slot this firing belongs to.

    APScheduler never fires early, and triggers are aligned to slot boundaries,
    so all workers land in the same slot.
    """
    timestamp = (now or datetime.now(UTC)).timestamp()
    return datetime.fromtimestamp(timestamp // slot_seconds * slot_seconds, tz=UTC)


async def run_job(
    job_key: str,
    job: JobFunction,
    *,
    slot_seconds: int = 60,
    now: datetime | None = None,
) -> bool:
    """Run ``job`` unless another worker has claimed this slot. True if it ran here."""
    slot = current_slot(slot_seconds, now)
    worker = _worker_name()

    async with SessionLocal() as db:
        locked = await db.scalar(
            select(func.pg_try_advisory_xact_lock(_lock_key(f"{job_key}:{slot.isoformat()}")))
        )
        if not locked:
            logger.info("Job %s, slot %s: claimed by another worker", job_key, slot.isoformat())
            return False
        institution = await get_institution(db)
        run_id = await db.scalar(
            insert(JobRun)
            .values(
                institution_id=institution.id,
                job_key=job_key,
                slot=slot,
                status="running",
                worker=worker,
            )
            .on_conflict_do_nothing(constraint="uq_job_runs_slot")
            .returning(JobRun.id)
        )
        await db.commit()
    if run_id is None:
        logger.info("Job %s, slot %s: already ran", job_key, slot.isoformat())
        return False

    try:
        result = await job() or JobResult()
    except Exception as exc:  # noqa: BLE001 - one failing job must not stop the scheduler
        logger.exception("Job %s failed", job_key)
        result = JobResult("failed", f"{type(exc).__name__}: {exc}"[:2000])

    async with SessionLocal() as db:
        await db.execute(
            update(JobRun)
            .where(JobRun.id == run_id)
            .values(status=result.status, detail=result.detail, finished_at=func.now())
        )
        await db.commit()
    logger.info("Job %s, slot %s: %s", job_key, slot.isoformat(), result.status)
    return True


async def housekeeping() -> JobResult:
    """Clear expired tokens and counters, and close runs orphaned by a crash."""
    now = datetime.now(UTC)
    cutoff = now - RETAIN_EXPIRED_TOKENS_FOR
    async with SessionLocal() as db:
        sessions = await db.execute(delete(RefreshToken).where(RefreshToken.expires_at < cutoff))
        resets = await db.execute(
            delete(PasswordResetToken).where(PasswordResetToken.expires_at < cutoff)
        )
        counters = await delete_expired_hits(db, older_than=now - timedelta(days=2))
        stale = await db.execute(
            update(JobRun)
            .where(JobRun.status == "running", JobRun.started_at < now - STALE_RUN_AFTER)
            .values(
                status="failed",
                detail="The worker stopped before this run finished.",
                finished_at=now,
            )
        )
        await db.execute(delete(JobRun).where(JobRun.started_at < now - RETAIN_JOB_RUNS_FOR))
        await db.commit()
    return JobResult(
        detail=(
            f"Removed {sessions.rowcount} sessions, {resets.rowcount} reset links, "
            f"{counters} rate-limit counters. Closed {stale.rowcount} stale runs."
        )
    )


async def scheduler_test_job() -> JobResult:
    """Does nothing. Each slot must end up with exactly one row (HANDOVER section 9)."""
    return JobResult(detail="single-firing check")


async def _run_backup() -> None:
    # Imported here because the backup service uses the job helpers in this module.
    from app.services.backup import prepare_backup

    await run_job(JOB_BACKUP, prepare_backup)


async def _run_housekeeping() -> None:
    await run_job(JOB_HOUSEKEEPING, housekeeping)


async def _run_scheduler_test(interval: int) -> None:
    await run_job(JOB_SCHEDULER_TEST, scheduler_test_job, slot_seconds=interval)


async def start_scheduler() -> None:
    """Start this worker's scheduler. Called from the application lifespan."""
    global _scheduler
    settings = get_settings()
    if _scheduler is not None or not settings.SCHEDULER_ENABLED:
        return

    async with SessionLocal() as db:
        timezone = (await get_institution(db)).timezone

    scheduler = AsyncIOScheduler(timezone=UTC)
    shared = {"coalesce": True, "max_instances": 1, "misfire_grace_time": 3600}
    scheduler.add_job(
        _run_backup,
        CronTrigger(hour=settings.BACKUP_HOUR, minute=0, timezone=timezone),
        id=JOB_BACKUP,
        **shared,
    )
    scheduler.add_job(
        _run_housekeeping,
        CronTrigger(hour=(settings.BACKUP_HOUR + 1) % 24, minute=0, timezone=timezone),
        id=JOB_HOUSEKEEPING,
        **shared,
    )
    interval = settings.SCHEDULER_TEST_INTERVAL_SECONDS
    if interval:
        logger.warning("Scheduler test job is on: every %d seconds", interval)
        scheduler.add_job(
            _run_scheduler_test,
            IntervalTrigger(
                seconds=interval,
                start_date=current_slot(interval) + timedelta(seconds=interval),
                timezone=UTC,
            ),
            args=[interval],
            id=JOB_SCHEDULER_TEST,
            coalesce=True,
            max_instances=1,
            misfire_grace_time=interval,
        )
    scheduler.start()
    _scheduler = scheduler
    logger.info("Scheduler started with %d jobs", len(scheduler.get_jobs()))


async def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
