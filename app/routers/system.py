"""Admin views of scheduled jobs and backups. Settings → Data shows them from step 1.3."""

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.deps import require_admin
from app.models.system import JobRun
from app.models.user import User
from app.services import backup as backup_service
from app.services.scheduler import JOB_BACKUP, JOB_BACKUP_MANUAL, run_job

router = APIRouter(tags=["system"])


class JobRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_key: str
    slot: datetime
    status: str
    detail: str | None
    worker: str | None
    started_at: datetime
    finished_at: datetime | None


class BackupStatus(BaseModel):
    configured: bool
    retention_days: int
    latest: dict | None
    last_run: JobRunOut | None


@router.get("/jobs/runs", response_model=list[JobRunOut])
async def list_job_runs(
    job_key: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[JobRun]:
    query = select(JobRun).where(JobRun.institution_id == admin.institution_id)
    if job_key:
        query = query.where(JobRun.job_key == job_key)
    runs = await db.scalars(query.order_by(JobRun.started_at.desc()).limit(limit))
    return list(runs)


@router.get("/backups/status", response_model=BackupStatus)
async def backup_status(
    admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)
) -> BackupStatus:
    settings = get_settings()
    last_run = await db.scalar(
        select(JobRun)
        .where(
            JobRun.institution_id == admin.institution_id,
            JobRun.job_key.in_([JOB_BACKUP, JOB_BACKUP_MANUAL]),
        )
        .order_by(JobRun.started_at.desc())
        .limit(1)
    )
    return BackupStatus(
        configured=bool(settings.BACKUP_PASSPHRASE),
        retention_days=settings.BACKUP_RETENTION_DAYS,
        latest=backup_service.latest_backup_info(),
        last_run=JobRunOut.model_validate(last_run) if last_run else None,
    )


@router.post("/backups/run", status_code=status.HTTP_202_ACCEPTED)
async def run_backup_now(
    background: BackgroundTasks, _: User = Depends(require_admin)
) -> dict[str, bool]:
    if not get_settings().BACKUP_PASSPHRASE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="backup_not_configured")
    background.add_task(run_job, JOB_BACKUP_MANUAL, backup_service.prepare_backup)
    return {"started": True}
