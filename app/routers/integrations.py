"""Settings → Integrations (admins): Google Analytics for website views (R8.1.1).

The key is uploaded by an admin in their own browser, so it never passes through anyone
else. It is stored Fernet-encrypted and never sent back: the page shows the service
account's address, its project and the property ID only.
"""

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import require_admin
from app.models.institution import Institution
from app.models.integration import KIND_GA4, Integration
from app.models.release import Measure, Reading, Release
from app.models.system import JobRun
from app.models.user import User
from app.routers.system import JobRunOut
from app.services import crypto, ga4
from app.services.field_patch import FieldConflict, FieldPatch, field_error, patch_result
from app.services.readings import SOURCE_AUTO, STATE_VALUE, today_in
from app.services.scheduler import JOB_GA4, JOB_GA4_MANUAL, STALE_RUN_AFTER, run_ga4

router = APIRouter(prefix="/integrations", tags=["integrations"])

# A key file is about 2.4 KB.
_MAX_KEY_LENGTH = 20_000
_PROPERTY = "property_id"


class KeyUpload(BaseModel):
    # The text of the downloaded JSON file. Never logged, never echoed back.
    key: str = Field(max_length=_MAX_KEY_LENGTH)


class WaitingRelease(BaseModel):
    release_id: UUID
    code: str | None
    title: str | None
    website_url: str
    release_date: date


class Ga4Status(BaseModel):
    # A key is stored, and whether this install can read it (another FERNET_KEY cannot).
    configured: bool
    readable: bool
    client_email: str | None
    project_id: str | None
    property_id: str | None
    field_versions: dict[str, int]
    domain: str | None
    first_fetch_at: datetime | None
    last_test_at: datetime | None
    last_test: dict[str, Any] | None
    last_run: JobRunOut | None
    running: bool
    # Website views fetched so far, and the releases still waiting: their 28 days and the
    # processing days have passed, yet nothing is there (after a fetch: no data for the path).
    fetched: int
    waiting: list[WaitingRelease]
    not_yet_due: int


async def _integration(db: AsyncSession, institution_id: UUID) -> Integration:
    """The row, made on first use, locked until commit."""
    integration = await ga4.load_integration(db, institution_id, for_update=True)
    if integration is None:
        integration = Integration(institution_id=institution_id, kind=KIND_GA4, config={})
        db.add(integration)
        await db.flush()
    return integration


async def _status(db: AsyncSession, institution: Institution) -> Ga4Status:
    integration = await ga4.load_integration(db, institution.id)
    config = (integration.config if integration else None) or {}
    readable = False
    if integration is not None and integration.credential is not None:
        try:
            ga4.stored_account(integration)
            readable = True
        except ga4.Ga4Error:
            readable = False
    runs = select(JobRun).where(
        JobRun.institution_id == institution.id, JobRun.job_key.in_([JOB_GA4, JOB_GA4_MANUAL])
    )
    last_run = await db.scalar(
        runs.where(JobRun.status != "running").order_by(JobRun.started_at.desc()).limit(1)
    )
    running = await db.scalar(
        runs.where(
            JobRun.status == "running",
            JobRun.started_at > datetime.now(UTC) - STALE_RUN_AFTER,
        ).limit(1)
    )
    today = today_in(institution.timezone)
    domain = institution.website_domain.strip().lower() if institution.website_domain else None
    waiting, still_open = await ga4.candidates(db, institution.id, domain, today)
    titles = {
        row.id: row.title
        for row in (
            await db.execute(
                select(Release.id, Release.title).where(
                    Release.id.in_([item.release_id for item in waiting])
                )
            )
        ).all()
    }
    fetched = await db.scalar(
        select(func.count())
        .select_from(Reading)
        .join(Measure, Measure.id == Reading.measure_id)
        .join(Release, Release.id == Reading.release_id)
        .where(
            Release.institution_id == institution.id,
            Release.deleted_at.is_(None),
            Measure.source == ga4.SOURCE,
            Reading.state == STATE_VALUE,
            Reading.source == SOURCE_AUTO,
        )
    )
    return Ga4Status(
        configured=integration is not None and integration.credential is not None,
        readable=readable,
        client_email=config.get("client_email"),
        project_id=config.get("project_id"),
        property_id=config.get(_PROPERTY),
        field_versions=(integration.field_versions if integration else None) or {},
        domain=domain,
        first_fetch_at=integration.first_fetch_at if integration else None,
        last_test_at=integration.last_test_at if integration else None,
        last_test=integration.last_test_result if integration else None,
        last_run=JobRunOut.model_validate(last_run) if last_run else None,
        running=running is not None,
        fetched=fetched or 0,
        waiting=[
            WaitingRelease(
                release_id=item.release_id,
                code=item.code,
                title=titles.get(item.release_id),
                website_url=item.website_url,
                release_date=item.release_date,
            )
            for item in waiting
        ],
        not_yet_due=len(still_open),
    )


@router.get("/ga4", response_model=Ga4Status)
async def get_ga4(
    admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)
) -> Ga4Status:
    return await _status(db, await db.get(Institution, admin.institution_id))


@router.put("/ga4/key", response_model=Ga4Status)
async def put_ga4_key(
    upload: KeyUpload,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Ga4Status:
    """Store a service account's JSON key, replacing any earlier one."""
    try:
        account = ga4.parse_key(upload.key)
    except ga4.Ga4Error as exc:
        raise field_error(f"ga4_{exc.code}") from None
    institution = await db.get(Institution, admin.institution_id)
    integration = await _integration(db, institution.id)
    integration.credential = crypto.encrypt(upload.key)
    integration.config = {**integration.config, **account.shown()}
    # A test of the old key says nothing about this one.
    integration.last_test_at = None
    integration.last_test_result = None
    await db.commit()
    return await _status(db, institution)


@router.delete("/ga4/key", response_model=Ga4Status)
async def delete_ga4_key(
    admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)
) -> Ga4Status:
    """Forget the key. Website views already fetched stay; the property ID stays too."""
    institution = await db.get(Institution, admin.institution_id)
    integration = await ga4.load_integration(db, institution.id, for_update=True)
    if integration is not None:
        integration.credential = None
        integration.config = {
            key: value
            for key, value in integration.config.items()
            if key not in {"client_email", "project_id"}
        }
        integration.last_test_at = None
        integration.last_test_result = None
        await db.commit()
    return await _status(db, institution)


@router.patch("/ga4")
async def patch_ga4(
    patch: FieldPatch,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """The property ID, saved like any other settings field (R3.3.3)."""
    if patch.field != _PROPERTY:
        raise field_error("field_not_editable")
    integration = await _integration(db, admin.institution_id)
    current = integration.config.get(_PROPERTY)
    version = integration.field_versions.get(_PROPERTY, 0)
    if patch.version != version:
        raise FieldConflict(_PROPERTY, current, version)
    raw = patch.value
    if raw is not None and not isinstance(raw, str | int):
        raise field_error("field_invalid")
    # "properties/123456789", as Google writes it in places, and spaces from copying.
    value = str(raw or "").strip().removeprefix("properties/").replace(" ", "") or None
    if value is not None and not ga4.valid_property_id(value):
        raise field_error("ga4_property_digits")
    if value != current:
        config = {key: item for key, item in integration.config.items() if key != _PROPERTY}
        integration.config = {**config, _PROPERTY: value} if value else config
        version += 1
        integration.field_versions = {**integration.field_versions, _PROPERTY: version}
        integration.last_test_at = None
        integration.last_test_result = None
    await db.commit()
    return patch_result(_PROPERTY, value, version)


def _ready(integration: Integration | None) -> tuple[ga4.ServiceAccount, str]:
    try:
        account = ga4.stored_account(integration)
    except ga4.Ga4Error as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"ga4_{exc.code}") from None
    property_id = integration.config.get(_PROPERTY)
    if not property_id:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="ga4_no_property")
    return account, property_id


@router.post("/ga4/test")
async def test_ga4(
    admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """A one-day report, saying in plain words what failed."""
    institution = await db.get(Institution, admin.institution_id)
    integration = await ga4.load_integration(db, institution.id)
    account, property_id = _ready(integration)
    domain = institution.website_domain.strip().lower() if institution.website_domain else None
    institution_id, today = institution.id, today_in(institution.timezone)
    # Nothing is held while Google answers.
    await db.rollback()
    result = await ga4.test_connection(account, property_id, domain, today)
    integration = await ga4.load_integration(db, institution_id, for_update=True)
    if integration is not None:
        integration.last_test_at = datetime.now(UTC)
        integration.last_test_result = result
        await db.commit()
    return result


@router.post("/ga4/fetch", status_code=status.HTTP_202_ACCEPTED)
async def fetch_ga4_now(
    background: BackgroundTasks,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    """Fetch now: the same run as the daily one, started by hand. The first one is the
    backfill, and daily runs start after it."""
    integration = await ga4.load_integration(db, admin.institution_id)
    _ready(integration)
    background.add_task(run_ga4, manual=True)
    return {"started": True}
