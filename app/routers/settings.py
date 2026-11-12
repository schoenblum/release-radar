"""Settings: the institution, checkpoints, measures and core-field configuration.

Anything a rule reads re-runs the rules across all releases, because rules otherwise run
only when a release is saved. Saves go through the ORM, so all of it reaches the audit log.
"""

import re
from typing import Any
from uuid import UUID
from zoneinfo import available_timezones

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user, require_admin
from app.models import Checkpoint, CoreFieldConfig, Institution, Measure, ReleaseType
from app.models.user import User
from app.schemas.settings import (
    CheckpointOut,
    CoreFieldOut,
    CreateEntry,
    InstitutionOut,
    MeasureCreate,
    MeasureOut,
    Reorder,
)
from app.services import field_patch, time_zones
from app.services.field_patch import (
    FieldPatch,
    FieldSpec,
    clean_value,
    commit_unique,
    field_error,
    load_for_update,
    patch_field,
    patch_result,
    set_versioned,
)
from app.services.readings import resync_institution

router = APIRouter(tags=["settings"])

_DOMAIN = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")
LANDING_ROLES = {"admin", "editor", "viewer"}
LANDING_VIEWS = {"mine", "all", "analysis"}
# The grid and the date logic rely on these, so they stay visible.
# A record without these makes no sense, nor a grid without the first two.
ALWAYS_IN_RECORD = frozenset({"code", "title", "release_date"})
ALWAYS_IN_GRID = frozenset({"code", "title"})
# The system assigns the code (D35), so nobody can be asked to fill it in.
# A gender belongs to the researcher, and is often not known: never required of a release.
NOT_REQUIRABLE = frozenset({"code", "researcher_gender"})


def _parse_timezone(value: Any) -> str:
    if not isinstance(value, str) or value not in available_timezones():
        raise field_error("invalid_timezone")
    return value


def _parse_domain(value: Any) -> str | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if not isinstance(value, str):
        raise field_error("invalid_domain")
    # A pasted address works too.
    host = re.sub(r"^[a-z]+://", "", value.strip().lower()).split("/")[0]
    if not _DOMAIN.match(host):
        raise field_error("invalid_domain")
    return host


def _parse_code_pattern(value: Any) -> str:
    # A code is never longer than its pattern, and codes are stored in 32 characters.
    if not isinstance(value, str) or len(value) > 32:
        raise field_error("invalid_code_pattern")
    value = value.strip()
    placeholders = re.findall(r"\{[^}]*\}", value)
    if sorted(placeholders) != ["{nn}", "{yyyy}"]:
        raise field_error("invalid_code_pattern")
    return value


def _parse_landing_pages(value: Any) -> dict[str, str]:
    if (
        not isinstance(value, dict)
        or set(value) != LANDING_ROLES
        or not set(value.values()) <= LANDING_VIEWS
    ):
        raise field_error("field_invalid")
    return value


def _parse_type_ids(value: Any) -> list[str]:
    """A list of release type IDs, each once, as text. Empty means every type."""
    if not isinstance(value, list):
        raise field_error("field_invalid")
    found: list[str] = []
    for item in value:
        try:
            text = str(UUID(str(item)))
        except ValueError as exc:
            raise field_error("field_invalid") from exc
        if text not in found:
            found.append(text)
    return found


def _parse_time_zones(value: Any) -> list[str | None]:
    """Up to three further zones to show release times in, in the order they show: any IANA
    zone, or None for a place left empty (Daniel, 2026-11-12). A zone named twice keeps its
    first place; empty places at the end are dropped."""
    if not isinstance(value, list):
        raise field_error("invalid_timezone")
    if len(value) > time_zones.MAX_SHOWN:
        raise field_error("too_many_time_zones")
    known = available_timezones()
    chosen: list[str | None] = []
    for item in value:
        if item is not None and (not isinstance(item, str) or item not in known):
            raise field_error("invalid_timezone")
        chosen.append(None if item in chosen else item)
    while chosen and chosen[-1] is None:
        chosen.pop()
    return chosen


# Where the two Analysis filters start (R6.4.2, R8.4.1).
_ANALYSIS_DEFAULTS = ("analysed_release_type_ids", "shown_release_type_ids")

INSTITUTION_SPECS: dict[str, FieldSpec] = {
    "name_en": field_patch.text(required=True),
    "name_ja": field_patch.text(),
    "timezone": FieldSpec(_parse_timezone),
    "ay_start_month": field_patch.integer(1, 12),
    "website_domain": FieldSpec(_parse_domain),
    "release_code_pattern": FieldSpec(_parse_code_pattern),
    "landing_pages": FieldSpec(_parse_landing_pages),
    "contact_email": field_patch.email(),
    # R6.4.1: what new releases start as; empty means they start with no type.
    "default_release_type_id": field_patch.reference(ReleaseType),
    "analysed_release_type_ids": FieldSpec(_parse_type_ids),
    "shown_release_type_ids": FieldSpec(_parse_type_ids),
    "display_time_zones": FieldSpec(_parse_time_zones),
}
CHECKPOINT_SPECS: dict[str, FieldSpec] = {
    "label_en": field_patch.text(required=True),
    "label_ja": field_patch.text(),
    # Negative falls before the release date (R6.5.3).
    "offset_days": field_patch.integer(-365, 3650),
    "remind_days_before": field_patch.integer(0, 1),
}
CHECKPOINT_DEFAULTS: dict[str, Any] = {"remind_days_before": 0}
MEASURE_SPECS: dict[str, FieldSpec] = {
    "label_en": field_patch.text(required=True),
    "label_ja": field_patch.text(),
    "is_active": field_patch.boolean(),
    "collected_from": field_patch.iso_date(),
}
CORE_FIELD_SPECS: dict[str, FieldSpec] = {
    "label_en": field_patch.text(),
    "label_ja": field_patch.text(),
    "in_record": field_patch.boolean(),
    "in_grid": field_patch.boolean(),
    "required": field_patch.boolean(),
}


async def _resync(db: AsyncSession, institution_id: UUID) -> None:
    await db.flush()
    await db.run_sync(resync_institution, institution_id)


# ---------------------------------------------------------------- institution


@router.get("/settings/institution", response_model=InstitutionOut)
async def get_institution_settings(
    admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)
) -> Institution:
    return await db.get(Institution, admin.institution_id)


@router.patch("/settings/institution")
async def patch_institution(
    patch: FieldPatch,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    institution = await db.scalar(
        select(Institution)
        .where(Institution.id == admin.institution_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    before = institution.website_domain
    version = await patch_field(db, institution, INSTITUTION_SPECS, patch, institution.id)
    if institution.website_domain != before:
        await _resync(db, institution.id)
    if patch.field in _ANALYSIS_DEFAULTS:
        await _check_analysis_defaults(db, institution, patch.field)
    await commit_unique(db)
    return patch_result(patch.field, getattr(institution, patch.field), version)


async def _check_analysis_defaults(db: AsyncSession, institution: Institution, field: str) -> None:
    """Every ID must be one of this institution's types. *Shown* offers only what *analysed*
    includes (R8.4.1): a type taken out of *analysed* leaves *shown* too."""
    ids = getattr(institution, field) or []
    known = {
        str(row)
        for row in await db.scalars(
            select(ReleaseType.id).where(ReleaseType.institution_id == institution.id)
        )
    }
    if not set(ids) <= known:
        raise field_error("unknown_reference")
    analysed = institution.analysed_release_type_ids or []
    shown = institution.shown_release_type_ids or []
    if field == "shown_release_type_ids" and analysed and not set(shown) <= set(analysed):
        raise field_error("shown_outside_analysed")
    if field == "analysed_release_type_ids" and analysed and not set(shown) <= set(analysed):
        kept = [item for item in shown if item in analysed]
        set_versioned(institution, "shown_release_type_ids", kept or list(analysed))


# ---------------------------------------------------------------- checkpoints


@router.get("/checkpoints", response_model=list[CheckpointOut])
async def list_checkpoints(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[Checkpoint]:
    rows = await db.scalars(
        select(Checkpoint)
        .where(Checkpoint.institution_id == user.institution_id)
        .order_by(Checkpoint.offset_days, Checkpoint.key)
    )
    return list(rows)


@router.post("/checkpoints", response_model=CheckpointOut, status_code=status.HTTP_201_CREATED)
async def create_checkpoint(
    payload: CreateEntry,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Checkpoint:
    values = {
        field: await clean_value(
            db,
            admin.institution_id,
            spec,
            payload.values.get(field, CHECKPOINT_DEFAULTS.get(field)),
        )
        for field, spec in CHECKPOINT_SPECS.items()
    }
    checkpoint = Checkpoint(
        institution_id=admin.institution_id, key=f"d{values['offset_days']}", **values
    )
    db.add(checkpoint)
    await commit_unique(db)
    return checkpoint


@router.patch("/checkpoints/{checkpoint_id}")
async def patch_checkpoint(
    checkpoint_id: UUID,
    patch: FieldPatch,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Moving an offset moves due dates by itself: they are computed, not stored."""
    checkpoint = await load_for_update(db, Checkpoint, checkpoint_id, admin.institution_id)
    version = await patch_field(db, checkpoint, CHECKPOINT_SPECS, patch, admin.institution_id)
    await commit_unique(db)
    return patch_result(patch.field, getattr(checkpoint, patch.field), version)


# ---------------------------------------------------------------- measures


@router.get("/measures", response_model=list[MeasureOut])
async def list_measures(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[Measure]:
    rows = await db.scalars(
        select(Measure)
        .where(Measure.institution_id == user.institution_id)
        .order_by(Measure.position, Measure.key)
    )
    return list(rows)


@router.post("/measures", response_model=MeasureOut, status_code=status.HTTP_201_CREATED)
async def create_measure(
    payload: MeasureCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Measure:
    """A known metric at another checkpoint, so that an added checkpoint can be used."""
    institution_id = admin.institution_id
    template = await db.scalar(
        select(Measure)
        .where(
            Measure.institution_id == institution_id,
            Measure.metric == payload.metric,
            Measure.source != "derived",
        )
        .limit(1)
    )
    if template is None:
        raise field_error("unknown_reference")
    checkpoint = await db.get(Checkpoint, payload.checkpoint_id)
    if checkpoint is None or checkpoint.institution_id != institution_id:
        raise field_error("unknown_reference")
    position = await db.scalar(
        select(func.coalesce(func.max(Measure.position), -1)).where(
            Measure.institution_id == institution_id
        )
    )
    measure = Measure(
        institution_id=institution_id,
        key=f"{payload.metric}.{checkpoint.key}",
        metric=payload.metric,
        checkpoint_id=checkpoint.id,
        source=template.source,
        applicability=template.applicability,
        unit=template.unit,
        label_en=await clean_value(db, institution_id, MEASURE_SPECS["label_en"], payload.label_en),
        label_ja=await clean_value(db, institution_id, MEASURE_SPECS["label_ja"], payload.label_ja),
        position=position + 1,
    )
    db.add(measure)
    await _resync(db, institution_id)
    await commit_unique(db)
    return measure


@router.patch("/measures/{measure_id}")
async def patch_measure(
    measure_id: UUID,
    patch: FieldPatch,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    measure = await load_for_update(db, Measure, measure_id, admin.institution_id)
    # Derived counts go live with their phase, once something can produce them (R10.10).
    if measure.source == "derived" and patch.field in ("is_active", "collected_from"):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="measure_locked")
    version = await patch_field(db, measure, MEASURE_SPECS, patch, admin.institution_id)
    if patch.field in ("is_active", "collected_from"):
        await _resync(db, admin.institution_id)
    await commit_unique(db)
    return patch_result(patch.field, getattr(measure, patch.field), version)


# ---------------------------------------------------------------- core fields


def _core_field_out(config: CoreFieldConfig) -> CoreFieldOut:
    return CoreFieldOut(
        id=config.id,
        key=config.key,
        label_en=config.label_en,
        label_ja=config.label_ja,
        in_record=config.in_record,
        in_grid=config.in_grid,
        required=config.required,
        position=config.position,
        can_leave_record=config.key not in ALWAYS_IN_RECORD,
        can_leave_grid=config.key not in ALWAYS_IN_GRID,
        can_require=config.key not in NOT_REQUIRABLE,
        field_versions=config.field_versions,
    )


@router.get("/core-fields", response_model=list[CoreFieldOut])
async def list_core_fields(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[CoreFieldOut]:
    rows = await db.scalars(
        select(CoreFieldConfig)
        .where(CoreFieldConfig.institution_id == user.institution_id)
        .order_by(CoreFieldConfig.position)
    )
    return [_core_field_out(config) for config in rows]


@router.patch("/core-fields/{config_id}")
async def patch_core_field(
    config_id: UUID,
    patch: FieldPatch,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    config = await load_for_update(db, CoreFieldConfig, config_id, admin.institution_id)
    if (
        (patch.field == "in_record" and patch.value is False and config.key in ALWAYS_IN_RECORD)
        or (patch.field == "in_grid" and patch.value is False and config.key in ALWAYS_IN_GRID)
        or (patch.field == "required" and patch.value and config.key in NOT_REQUIRABLE)
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="core_field_locked")
    version = await patch_field(db, config, CORE_FIELD_SPECS, patch, admin.institution_id)
    await commit_unique(db)
    return patch_result(patch.field, getattr(config, patch.field), version)


@router.post("/core-fields/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_core_fields(
    payload: Reorder,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    rows = {
        config.id: config
        for config in await db.scalars(
            select(CoreFieldConfig)
            .where(CoreFieldConfig.institution_id == admin.institution_id)
            .with_for_update()
        )
    }
    if set(payload.ids) != set(rows):
        raise field_error("field_invalid")
    for position, config_id in enumerate(payload.ids):
        rows[config_id].position = position
    await db.commit()
