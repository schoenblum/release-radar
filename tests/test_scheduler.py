"""Single-firing and visible job status. These run against real Postgres locks."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import Institution, JobRun, PasswordResetToken, RateLimitHit, RefreshToken, User
from app.services import scheduler
from app.services.scheduler import JobResult, current_slot, housekeeping, run_job
from tests.conftest import sign_in

NOW = datetime(2026, 4, 1, 3, 0, 0, 5000, tzinfo=UTC)


async def _runs(job_key: str = "test-job") -> list[JobRun]:
    async with SessionLocal() as db:
        rows = await db.scalars(
            select(JobRun).where(JobRun.job_key == job_key).order_by(JobRun.slot)
        )
        return list(rows)


async def test_concurrent_workers_run_a_slot_exactly_once():
    calls = 0

    async def job() -> None:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)

    outcomes = await asyncio.gather(*(run_job("test-job", job, now=NOW) for _ in range(8)))

    assert calls == 1
    assert sum(outcomes) == 1
    assert len(await _runs()) == 1


async def test_worker_arriving_after_the_first_finished_does_not_run_it_again():
    """An advisory lock alone would allow this: it is released when the first worker commits."""
    calls = 0

    async def job() -> None:
        nonlocal calls
        calls += 1

    assert await run_job("test-job", job, now=NOW) is True
    assert await run_job("test-job", job, now=NOW + timedelta(seconds=20)) is False
    assert calls == 1


async def test_next_slot_runs_again():
    calls = 0

    async def job() -> None:
        nonlocal calls
        calls += 1

    await run_job("test-job", job, now=NOW)
    await run_job("test-job", job, now=NOW + timedelta(seconds=60))
    assert calls == 2
    assert len(await _runs()) == 2


async def test_different_jobs_do_not_block_each_other():
    async def job() -> None:
        return None

    assert await run_job("job-a", job, now=NOW) is True
    assert await run_job("job-b", job, now=NOW) is True


async def test_success_is_recorded():
    async def job() -> JobResult:
        return JobResult(detail="all fine")

    await run_job("test-job", job, now=NOW)
    run = (await _runs())[0]
    assert run.status == "succeeded"
    assert run.detail == "all fine"
    assert run.finished_at is not None
    assert run.worker
    assert run.slot == datetime(2026, 4, 1, 3, 0, tzinfo=UTC)


async def test_skip_is_recorded_with_its_reason():
    async def job() -> JobResult:
        return JobResult("skipped", "No API key configured.")

    await run_job("test-job", job, now=NOW)
    run = (await _runs())[0]
    assert run.status == "skipped"
    assert run.detail == "No API key configured."


async def test_crash_is_recorded_and_does_not_escape():
    async def job() -> None:
        raise ValueError("boom")

    assert await run_job("test-job", job, now=NOW) is True
    run = (await _runs())[0]
    assert run.status == "failed"
    assert run.detail == "ValueError: boom"


@pytest.mark.parametrize(
    ("moment", "seconds", "expected"),
    [
        ("2026-04-01T03:00:00.005+00:00", 60, "2026-04-01T03:00:00+00:00"),
        ("2026-04-01T03:00:59.999+00:00", 60, "2026-04-01T03:00:00+00:00"),
        ("2026-04-01T03:00:31+00:00", 30, "2026-04-01T03:00:30+00:00"),
    ],
)
def test_slots_start_on_their_boundary(moment, seconds, expected):
    slot = current_slot(seconds, datetime.fromisoformat(moment))
    assert slot == datetime.fromisoformat(expected)


async def test_housekeeping_clears_old_tokens_and_closes_stale_runs(client, make_user):
    user = await make_user()
    await sign_in(client, "editor@example.org", "correct-horse-battery")
    now = datetime.now(UTC)
    long_ago = now - timedelta(days=40)

    async with SessionLocal() as db:
        institution_id = await db.scalar(select(Institution.id))
        db.add_all(
            [
                RefreshToken(
                    institution_id=institution_id,
                    user_id=user.id,
                    token_hash="a" * 64,
                    expires_at=long_ago,
                ),
                PasswordResetToken(
                    institution_id=institution_id,
                    user_id=user.id,
                    token_hash="b" * 64,
                    expires_at=long_ago,
                ),
                RateLimitHit(
                    institution_id=institution_id,
                    bucket="c" * 64,
                    window_start=long_ago,
                    count=3,
                ),
                JobRun(
                    institution_id=institution_id,
                    job_key="orphan",
                    slot=now - timedelta(hours=8),
                    status="running",
                    started_at=now - timedelta(hours=8),
                ),
                JobRun(
                    institution_id=institution_id,
                    job_key="in-progress",
                    slot=now,
                    status="running",
                    started_at=now,
                ),
            ]
        )
        await db.commit()

    result = await housekeeping()
    assert result.status == "succeeded"

    async with SessionLocal() as db:
        # The session just created stays, and the expired one goes.
        assert await db.scalar(select(func.count()).select_from(RefreshToken)) == 1
        assert await db.scalar(select(func.count()).select_from(PasswordResetToken)) == 0
        assert await db.scalar(select(func.count()).select_from(RateLimitHit)) == 0
    assert (await _runs("orphan"))[0].status == "failed"
    assert (await _runs("in-progress"))[0].status == "running"
    async with SessionLocal() as db:
        assert await db.get(User, user.id) is not None


async def test_start_registers_the_jobs_in_the_institution_time_zone(monkeypatch):
    settings = scheduler.get_settings()
    monkeypatch.setattr(settings, "SCHEDULER_ENABLED", True)
    monkeypatch.setattr(settings, "SCHEDULER_TEST_INTERVAL_SECONDS", 30)
    await scheduler.start_scheduler()
    try:
        jobs = {job.id: job for job in scheduler._scheduler.get_jobs()}
        assert set(jobs) == {
            scheduler.JOB_BACKUP,
            scheduler.JOB_HOUSEKEEPING,
            scheduler.JOB_SCHEDULER_TEST,
        }
        trigger = jobs[scheduler.JOB_BACKUP].trigger
        assert isinstance(trigger, CronTrigger)
        assert str(trigger.timezone) == "Asia/Tokyo"
    finally:
        await scheduler.stop_scheduler()


async def test_test_job_is_off_by_default(monkeypatch):
    settings = scheduler.get_settings()
    monkeypatch.setattr(settings, "SCHEDULER_ENABLED", True)
    await scheduler.start_scheduler()
    try:
        assert scheduler._scheduler.get_job(scheduler.JOB_SCHEDULER_TEST) is None
    finally:
        await scheduler.stop_scheduler()
