"""Releases and their readings (step 1.4).

Each field saves on its own with its own version, so two people editing different fields
never overwrite each other, and two editing the same one get to choose (R3.3.2, R3.3.3). Every
change goes through the ORM, so the applicability rules and the audit log run by themselves
(``app/record_events.py``).

Removing a release only hides it: Undo brings it back, and its code stays taken (D35).
"""

import re
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user, require_editor
from app.models import (
    AuditLog,
    Checkpoint,
    CoreFieldConfig,
    CustomField,
    Institution,
    Measure,
    Reading,
    Release,
    Researcher,
    ResearchField,
    Unit,
    User,
    UserRole,
    Writer,
)
from app.schemas.releases import (
    CrossrefRefetch,
    CrossrefRefetched,
    CustomValuePatch,
    DoiLookup,
    DoiLookupOut,
    DueItem,
    HistoryEntry,
    ReadingOut,
    ReadingPatch,
    ReleaseCreate,
    ReleaseCreated,
    ReleaseOut,
    ReleasePage,
    ReleaseSaved,
)
from app.services import crossref, custom_values, field_patch, release_filters
from app.services.field_patch import (
    FieldConflict,
    FieldPatch,
    FieldSpec,
    clean_value,
    commit_unique,
    field_error,
    parse_number,
    patch_field,
    patch_result,
    set_versioned,
)
from app.services.readings import (
    SOURCE_AUTO,
    SOURCE_MANUAL,
    STATE_MISSING,
    STATE_NOT_APPLICABLE,
    STATE_VALUE,
    display_state,
    due_date,
    measure_applies,
    on_domain,
    reminder_date,
    today_in,
)
from app.services.release_codes import academic_year, assign_code
from app.services.release_filters import ReleaseFilters

router = APIRouter(tags=["releases"])

# The largest number a reading can hold: numeric(14, 2).
_READING_LIMIT = Decimal("1e12")
_CENTS = Decimal("0.01")
# Only these measure units take decimals. The rest are counts (R7.5.8).
_DECIMAL_UNITS = frozenset({"score"})
# A reading's history leaves out what only supports these.
_READING_HISTORY_FIELDS = ("value", "state", "note")
_PAPER_FIELDS = ("journal", "paper_title", "publication_date", "authors")
# R7.5.1: besides what is due, what falls due in the next days.
_DUE_HORIZON_DAYS = 3
# Someone enters these by hand. Automatic and calculated measures ask nobody for anything.
_ASKED_FOR_SOURCE = "manual"
# Core-field settings use a name, and the release holds the reference.
_CORE_ATTRIBUTES = {
    "writer": "writer_id",
    "researcher": "researcher_id",
    "unit": "unit_id",
    "field": "field_id",
}
_ATTRIBUTE_CORE = {attribute: key for key, attribute in _CORE_ATTRIBUTES.items()}


def _parse_doi(value: Any) -> str | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    doi = crossref.normalise_doi(value) if isinstance(value, str) else None
    if doi is None:
        raise field_error("invalid_doi")
    return doi


def _parse_authors(value: Any) -> list[dict[str, str | None]]:
    """Editable, in the shape Crossref fills them in. A plain name is fine too."""
    if value is None or value == "":
        return []
    if not isinstance(value, list):
        raise field_error("field_invalid")
    authors = []
    for entry in value:
        if isinstance(entry, str):
            entry = {"name": entry}
        if not isinstance(entry, dict):
            raise field_error("field_invalid")
        author = {
            key: (entry.get(key).strip() or None) if isinstance(entry.get(key), str) else None
            for key in ("given", "family", "name", "orcid")
        }
        if not (author["given"] or author["family"] or author["name"]):
            raise field_error("field_invalid")
        authors.append(author)
    return authors


SPECS: dict[str, FieldSpec] = {
    "title": field_patch.text(2000),
    "title_ja": field_patch.text(2000),
    "writer_id": field_patch.reference(Writer),
    "researcher_id": field_patch.reference(Researcher),
    "also_featured": field_patch.text(2000),
    "unit_id": field_patch.reference(Unit),
    "field_id": field_patch.reference(ResearchField),
    "doi": FieldSpec(_parse_doi),
    "journal": field_patch.text(1000),
    "paper_title": field_patch.text(2000),
    "publication_date": field_patch.iso_date(),
    "authors": FieldSpec(_parse_authors),
    "embargoed": field_patch.boolean(),
    "release_date": field_patch.iso_date(),
    "release_time_et": field_patch.clock_time(),
    "ea_url": field_patch.web_address(),
    "website_url": field_patch.web_address(),
    "ea_top_page": field_patch.boolean(),
    "ea_top_position": field_patch.optional_integer(1, 999),
    "notes": field_patch.text(20000),
}


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == []


def _warnings(release: Release, institution: Institution) -> list[str]:
    """Saved anyway, but worth a look (R7.5.8)."""
    warnings = []
    if release.ea_url and not re.match(institution.ea_url_pattern, release.ea_url):
        warnings.append("ea_url_unusual")
    if (
        release.website_url
        and institution.website_domain
        and not on_domain(release, institution.website_domain)
    ):
        warnings.append("website_off_domain")
    return warnings


def _reading_out(
    reading: Reading,
    measure: Measure,
    checkpoint: Checkpoint | None,
    release_date: date | None,
    today: date,
) -> ReadingOut:
    due = due_date(release_date, checkpoint.offset_days if checkpoint else None)
    return ReadingOut(
        id=reading.id,
        measure_id=measure.id,
        measure_key=measure.key,
        value=float(reading.value) if reading.value is not None else None,
        state=reading.state,
        display_state=display_state(reading.state, due, today),
        source=reading.source,
        due_date=due,
        remind_on=reminder_date(due, checkpoint.remind_days_before) if checkpoint else None,
        note=reading.note,
        version=reading.version,
        entered_at=reading.entered_at,
    )


async def _present(
    db: AsyncSession, institution: Institution, releases: list[Release]
) -> list[ReleaseOut]:
    """Releases as the grid and the drawer need them, with no query per row."""
    if not releases:
        return []
    today = today_in(institution.timezone)
    release_ids = [release.id for release in releases]
    dates = {release.id: release.release_date for release in releases}

    # Only active measures: an inactive one counts as not applicable (R8.2.4).
    readings: dict[UUID, list[ReadingOut]] = defaultdict(list)
    rows = await db.execute(
        select(Reading, Measure, Checkpoint)
        .join(Measure, Measure.id == Reading.measure_id)
        .outerjoin(Checkpoint, Checkpoint.id == Measure.checkpoint_id)
        .where(Reading.release_id.in_(release_ids), Measure.is_active.is_(True))
        .order_by(Measure.position, Measure.key)
    )
    for reading, measure, checkpoint in rows.all():
        readings[reading.release_id].append(
            _reading_out(reading, measure, checkpoint, dates[reading.release_id], today)
        )

    researcher_ids = {release.researcher_id for release in releases if release.researcher_id}
    names = dict(
        (
            await db.execute(
                select(Researcher.id, Researcher.name).where(Researcher.id.in_(researcher_ids))
            )
        ).all()
    )
    required_core = list(
        await db.scalars(
            select(CoreFieldConfig.key).where(
                CoreFieldConfig.institution_id == institution.id,
                CoreFieldConfig.required.is_(True),
                CoreFieldConfig.hidden.is_(False),
            )
        )
    )
    required_custom = list(
        await db.scalars(
            select(CustomField.key).where(
                CustomField.institution_id == institution.id,
                CustomField.required.is_(True),
                CustomField.is_active.is_(True),
            )
        )
    )

    presented = []
    for release in releases:
        out = ReleaseOut.model_validate(release)
        out.readings = readings[release.id]
        out.researcher_name = names.get(release.researcher_id)
        if release.release_date is not None:
            out.academic_year = academic_year(release.release_date, institution.ay_start_month)
        out.warnings = _warnings(release, institution)
        out.missing_required = [
            key
            for key in required_core
            if _is_empty(getattr(release, _CORE_ATTRIBUTES.get(key, key)))
        ] + [f"custom_values.{key}" for key in required_custom if key not in release.custom_values]
        presented.append(out)
    return presented


async def _present_one(db: AsyncSession, institution: Institution, release: Release) -> ReleaseOut:
    return (await _present(db, institution, [release]))[0]


async def _load(
    db: AsyncSession,
    release_id: UUID,
    institution_id: UUID,
    *,
    lock: bool = False,
    deleted: bool = False,
) -> Release:
    statement = select(Release).where(
        Release.id == release_id,
        Release.institution_id == institution_id,
        Release.deleted_at.is_not(None) if deleted else Release.deleted_at.is_(None),
    )
    if lock:
        # Hold the row until commit, so two saves cannot interleave.
        statement = statement.with_for_update().execution_options(populate_existing=True)
    release = await db.scalar(statement)
    if release is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
    return release


def _fill_from_paper(release: Release, paper: crossref.Paper, *, overwrite: bool) -> None:
    """Crossref's answer never empties a field, and only an explicit refetch overwrites one."""
    for name in _PAPER_FIELDS:
        value = getattr(paper, name)
        current = getattr(release, name)
        if not _is_empty(value) and value != current and (overwrite or _is_empty(current)):
            set_versioned(release, name, value)


# ---------------------------------------------------------------- reading and creating


def filters_from_query(
    view: Literal["all", "mine"] = Query(default="all"),
    academic_year: int | None = Query(default=None, ge=1900, le=2999),
    field_id: UUID | None = Query(default=None),
    unit_id: UUID | None = Query(default=None),
    researcher_id: UUID | None = Query(default=None),
    writer_id: UUID | None = Query(default=None),
    q: str | None = Query(default=None, max_length=200),
) -> ReleaseFilters:
    return ReleaseFilters(
        view=view,
        academic_year=academic_year,
        field_id=field_id,
        unit_id=unit_id,
        researcher_id=researcher_id,
        writer_id=writer_id,
        search=q,
    )


# Newest first, with drafts on top.
NEWEST_FIRST = (Release.release_date.desc().nulls_first(), Release.created_at.desc(), Release.id)


@router.get("/releases", response_model=ReleasePage)
async def list_releases(
    filters: ReleaseFilters = Depends(filters_from_query),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReleasePage:
    """A view of the releases, newest first (R7.6.1). The grid sorts what it shows itself."""
    institution = await db.get(Institution, user.institution_id)
    writer_id = await release_filters.own_writer_id(db, user)
    where = release_filters.conditions(institution, filters, writer_id)
    total = await db.scalar(select(func.count()).select_from(Release).where(*where))
    if filters.narrowed:
        whole_view = ReleaseFilters(view=filters.view)
        view_total = await db.scalar(
            select(func.count())
            .select_from(Release)
            .where(*release_filters.conditions(institution, whole_view, writer_id))
        )
    else:
        view_total = total
    releases = list(
        await db.scalars(
            select(Release).where(*where).order_by(*NEWEST_FIRST).limit(limit).offset(offset)
        )
    )
    return ReleasePage(
        items=await _present(db, institution, releases),
        total=total or 0,
        view_total=view_total or 0,
        has_writer_entry=writer_id is not None,
        academic_years=await release_filters.academic_years(db, institution),
    )


@router.get("/releases/due", response_model=list[DueItem])
async def due_items(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DueItem]:
    """What this person is asked for, soonest first (R7.5.1): as writer, or as a field's owner.

    Items stay until filled or set N/A, with no notion of late (P5). A custom field is not
    asked for on dates before it existed: nobody can have been tracking it then.
    """
    if user.role == UserRole.viewer:
        return []
    institution = await db.get(Institution, user.institution_id)
    today = today_in(institution.timezone)
    horizon = today + timedelta(days=_DUE_HORIZON_DAYS)
    writer_id = await db.scalar(
        select(Writer.id).where(Writer.institution_id == institution.id, Writer.user_id == user.id)
    )
    is_live = [
        Release.institution_id == institution.id,
        Release.deleted_at.is_(None),
        Release.release_date.is_not(None),
    ]
    items: list[DueItem] = []

    def item(release: Release, due: date, label: Measure | CustomField, **extra: Any) -> DueItem:
        return DueItem(
            release_id=release.id,
            release_code=release.code,
            release_title=release.title,
            due_date=due,
            due_now=due <= today,
            label_en=label.label_en,
            label_ja=label.label_ja,
            **extra,
        )

    if writer_id is not None:
        rows = await db.execute(
            select(Reading, Measure, Checkpoint, Release)
            .join(Measure, Measure.id == Reading.measure_id)
            .join(Checkpoint, Checkpoint.id == Measure.checkpoint_id)
            .join(Release, Release.id == Reading.release_id)
            .where(
                *is_live,
                Release.writer_id == writer_id,
                Reading.state == STATE_MISSING,
                Measure.is_active.is_(True),
                Measure.source == _ASKED_FOR_SOURCE,
            )
        )
        for reading, measure, checkpoint, release in rows.all():
            due = due_date(release.release_date, checkpoint.offset_days)
            if due <= horizon:
                items.append(
                    item(
                        release,
                        due,
                        measure,
                        kind="reading",
                        version=reading.version,
                        reading_id=reading.id,
                        measure_key=measure.key,
                        measure_unit=measure.unit,
                    )
                )

    fields = (
        await db.execute(
            select(CustomField, Checkpoint)
            .join(Checkpoint, Checkpoint.id == CustomField.due_checkpoint_id)
            .where(
                CustomField.institution_id == institution.id,
                CustomField.is_active.is_(True),
                or_(CustomField.scope == "institution", CustomField.owner_id == user.id),
            )
        )
    ).all()
    if fields:
        zone = ZoneInfo(institution.timezone)
        releases = list(await db.scalars(select(Release).where(*is_live)))
        for field, checkpoint in fields:
            created = field.created_at.astimezone(zone).date()
            for release in releases:
                if field.scope == "institution" and release.writer_id != writer_id:
                    continue
                due = due_date(release.release_date, checkpoint.offset_days)
                if field.key in release.custom_values or due > horizon or due < created:
                    continue
                items.append(
                    item(
                        release,
                        due,
                        field,
                        kind="custom",
                        version=release.field_versions.get(f"custom_values.{field.key}", 0),
                        field_key=field.key,
                        field_type=field.field_type,
                    )
                )
    items.sort(key=lambda entry: (entry.due_date, entry.release_code or "", entry.label_en))
    return items


@router.post("/releases", response_model=ReleaseCreated, status_code=status.HTTP_201_CREATED)
async def create_release(
    payload: ReleaseCreate,
    user: User = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
) -> ReleaseCreated:
    """A draft from a title or a DOI (R7.5.4, R7.5.6). The writer defaults to this person."""
    institution = await db.get(Institution, user.institution_id)
    title = await clean_value(db, institution.id, SPECS["title"], payload.title)
    doi = await clean_value(db, institution.id, SPECS["doi"], payload.doi)
    if title is None and doi is None:
        raise field_error("title_or_doi_required")

    # Before anything is written, so no database row waits on another service.
    result = await crossref.lookup(doi, institution.contact_email) if doi else None
    writer_id = await db.scalar(
        select(Writer.id).where(Writer.institution_id == institution.id, Writer.user_id == user.id)
    )
    release = Release(institution_id=institution.id, title=title, doi=doi, writer_id=writer_id)
    if result is not None and result.paper is not None:
        for name in _PAPER_FIELDS:
            setattr(release, name, getattr(result.paper, name))
    db.add(release)
    await commit_unique(db)
    out = await _present_one(db, institution, release)
    return ReleaseCreated(**out.model_dump(), crossref=result.status if result else None)


@router.get("/releases/{release_id}", response_model=ReleaseOut)
async def get_release(
    release_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReleaseOut:
    institution = await db.get(Institution, user.institution_id)
    return await _present_one(db, institution, await _load(db, release_id, institution.id))


# ---------------------------------------------------------------- saving one field


async def _follow_researcher(db: AsyncSession, release: Release) -> None:
    """R7.5.4: the unit comes from the researcher, and then the field from the unit."""
    researcher = await db.get(Researcher, release.researcher_id)
    if researcher.merged_into_id is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="researcher_merged")
    if release.unit_id is None and researcher.current_unit_id is not None:
        set_versioned(release, "unit_id", researcher.current_unit_id)
        await _follow_unit(db, release)


async def _follow_unit(db: AsyncSession, release: Release) -> None:
    unit = await db.get(Unit, release.unit_id)
    if release.field_id is None and unit.default_field_id is not None:
        set_versioned(release, "field_id", unit.default_field_id)


async def _apply_consequences(
    db: AsyncSession, release: Release, field: str, institution: Institution
) -> None:
    """What one field's new value means for others. Only ever fills what is empty."""
    if field == "release_date":
        await assign_code(db, release, institution)
    elif field == "researcher_id" and release.researcher_id is not None:
        await _follow_researcher(db, release)
    elif field == "unit_id" and release.unit_id is not None:
        await _follow_unit(db, release)
    elif field == "ea_top_page" and not release.ea_top_page and release.ea_top_position is not None:
        set_versioned(release, "ea_top_position", None)
    elif field == "ea_top_position" and release.ea_top_position and not release.ea_top_page:
        set_versioned(release, "ea_top_page", True)


async def _refuse_emptying_a_required_field(
    db: AsyncSession, field: str, institution_id: UUID
) -> None:
    required = await db.scalar(
        select(CoreFieldConfig.required).where(
            CoreFieldConfig.institution_id == institution_id,
            CoreFieldConfig.key == _ATTRIBUTE_CORE.get(field, field),
            CoreFieldConfig.hidden.is_(False),
        )
    )
    if required:
        raise field_error("field_required")


@router.patch("/releases/{release_id}", response_model=ReleaseSaved)
async def patch_release(
    release_id: UUID,
    patch: FieldPatch,
    user: User = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Save one field. The answer carries the whole release, since one field can move others."""
    institution = await db.get(Institution, user.institution_id)
    release = await _load(db, release_id, institution.id, lock=True)
    version = await patch_field(db, release, SPECS, patch, institution.id)
    if release.title is None and release.doi is None:
        raise field_error("title_or_doi_required")
    if _is_empty(getattr(release, patch.field)):
        with db.no_autoflush:
            await _refuse_emptying_a_required_field(db, patch.field, institution.id)
    await _apply_consequences(db, release, patch.field, institution)
    await commit_unique(db)
    return {
        **patch_result(patch.field, getattr(release, patch.field), version),
        "release": await _present_one(db, institution, release),
    }


@router.patch("/releases/{release_id}/custom/{key}", response_model=ReleaseSaved)
async def patch_custom_value(
    release_id: UUID,
    key: str,
    patch: CustomValuePatch,
    user: User = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """One custom field. A personal field only by its owner, and a retired one by nobody."""
    institution = await db.get(Institution, user.institution_id)
    field = await db.scalar(
        select(CustomField).where(
            CustomField.institution_id == institution.id, CustomField.key == key
        )
    )
    if field is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
    if field.scope == "personal" and field.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="personal_field_read_only")
    if not field.is_active:
        raise field_error("field_not_editable")

    release = await _load(db, release_id, institution.id, lock=True)
    name = f"custom_values.{key}"
    version = release.field_versions.get(name, 0)
    current = release.custom_values.get(key)
    if patch.version != version:
        raise FieldConflict(name, current, version)

    if patch.state == custom_values.STATE_NOT_APPLICABLE:
        stored = {"state": custom_values.STATE_NOT_APPLICABLE}
    elif patch.state == STATE_MISSING:
        stored = None
    elif current is not None and patch.value is not None and patch.value == current.get("value"):
        # Unchanged, which also covers a choice that has since been retired.
        stored = current
    else:
        value = await custom_values.parse_value(db, field, patch.value)
        stored = None if value is None else {"state": custom_values.STATE_VALUE, "value": value}
    if stored is None and field.required:
        raise field_error("field_required")

    if stored != current:
        values = {name_: item for name_, item in release.custom_values.items() if name_ != key}
        if stored is not None:
            values[key] = stored
        release.custom_values = values
        version += 1
        release.field_versions = {**release.field_versions, name: version}
    await commit_unique(db)
    return {
        **patch_result(name, stored, version),
        "release": await _present_one(db, institution, release),
    }


# ---------------------------------------------------------------- readings


def _clean_reading_value(measure: Measure, raw: Any) -> Decimal:
    number = parse_number(raw)
    if number < 0 or number >= _READING_LIMIT:
        raise field_error("field_out_of_range")
    if measure.unit not in _DECIMAL_UNITS and number != number.to_integral_value():
        raise field_error("whole_number_required")
    return number.quantize(_CENTS)


@router.patch("/readings/{reading_id}", response_model=ReadingOut)
async def patch_reading(
    reading_id: UUID,
    patch: ReadingPatch,
    user: User = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
) -> ReadingOut:
    """Enter a number, set N/A, clear it, or add a note. Any time at all (P5, R6.5.2)."""
    institution = await db.get(Institution, user.institution_id)
    reading = await db.scalar(
        select(Reading)
        .where(Reading.id == reading_id, Reading.institution_id == institution.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if reading is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
    release = await _load(db, reading.release_id, institution.id)
    measure = await db.get(Measure, reading.measure_id)
    # Calculated counts go live with their phase, and are never entered (R10.10).
    if measure.source == "derived":
        raise HTTPException(status.HTTP_409_CONFLICT, detail="measure_locked")
    if patch.version != reading.version:
        raise FieldConflict(
            "value",
            float(reading.value) if reading.value is not None else None,
            reading.version,
            {"current_state": reading.state},
        )

    sent = patch.model_fields_set
    before = (reading.value, reading.state, reading.note)
    blank = patch.value is None or (isinstance(patch.value, str) and not patch.value.strip())
    if patch.state == STATE_NOT_APPLICABLE:
        reading.value = None
        reading.state = STATE_NOT_APPLICABLE
        reading.source = SOURCE_MANUAL
    elif patch.state == STATE_MISSING or ("value" in sent and blank):
        # Back to what the rules say, and from here on the rules may move it.
        applies = measure_applies(measure, release, institution.website_domain)
        reading.value = None
        reading.state = STATE_MISSING if applies else STATE_NOT_APPLICABLE
        reading.source = SOURCE_AUTO
    elif "value" in sent:
        reading.value = _clean_reading_value(measure, patch.value)
        reading.state = STATE_VALUE
        reading.source = SOURCE_MANUAL
    if "note" in sent:
        reading.note = await clean_value(db, institution.id, field_patch.text(2000), patch.note)

    if (reading.value, reading.state, reading.note) != before:
        reading.version += 1
        reading.entered_by_id = user.id
        reading.entered_at = datetime.now(UTC)
    await commit_unique(db)
    checkpoint = await db.get(Checkpoint, measure.checkpoint_id) if measure.checkpoint_id else None
    return _reading_out(
        reading, measure, checkpoint, release.release_date, today_in(institution.timezone)
    )


# ---------------------------------------------------------------- Crossref


@router.post("/lookup/doi", response_model=DoiLookupOut)
async def lookup_doi(
    payload: DoiLookup,
    user: User = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """What Crossref knows about a DOI. Saves nothing. An unknown DOI is an answer, not an error."""
    doi = _parse_doi(payload.doi)
    if doi is None:
        raise field_error("invalid_doi")
    contact = await db.scalar(
        select(Institution.contact_email).where(Institution.id == user.institution_id)
    )
    return {"doi": doi, **(await crossref.lookup(doi, contact)).as_dict()}


@router.post("/releases/{release_id}/crossref", response_model=CrossrefRefetched)
async def refetch_from_crossref(
    release_id: UUID,
    payload: CrossrefRefetch,
    user: User = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
) -> CrossrefRefetched:
    """The refetch button. Fills journal, paper title, publication date and authors."""
    institution = await db.get(Institution, user.institution_id)
    release = await _load(db, release_id, institution.id)
    if release.doi is None:
        raise field_error("invalid_doi")
    doi = release.doi
    # Nothing is locked while another service answers.
    await db.commit()
    result = await crossref.lookup(doi, institution.contact_email)

    release = await _load(db, release_id, institution.id, lock=True)
    # If the DOI changed meanwhile, this answer is about another paper.
    if result.paper is not None and release.doi == doi:
        _fill_from_paper(release, result.paper, overwrite=payload.overwrite)
    await commit_unique(db)
    return CrossrefRefetched(
        status=result.status, release=await _present_one(db, institution, release)
    )


# ---------------------------------------------------------------- removing, and history


@router.delete("/releases/{release_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_release(
    release_id: UUID,
    user: User = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
) -> None:
    release = await _load(db, release_id, user.institution_id, lock=True)
    release.deleted_at = datetime.now(UTC)
    await commit_unique(db)


@router.post("/releases/{release_id}/restore", response_model=ReleaseOut)
async def restore_release(
    release_id: UUID,
    user: User = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
) -> ReleaseOut:
    institution = await db.get(Institution, user.institution_id)
    release = await _load(db, release_id, institution.id, lock=True, deleted=True)
    release.deleted_at = None
    await commit_unique(db)
    return await _present_one(db, institution, release)


@router.get("/releases/{release_id}/history", response_model=list[HistoryEntry])
async def release_history(
    release_id: UUID,
    limit: int = Query(default=200, ge=1, le=1000),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[HistoryEntry]:
    """Who changed what, newest first, for the drawer (R3.4.4). Silent, never judged (P5)."""
    release = await _load(db, release_id, user.institution_id)
    measure_keys = dict(
        (
            await db.execute(
                select(Reading.id, Measure.key)
                .join(Measure, Measure.id == Reading.measure_id)
                .where(Reading.release_id == release.id)
            )
        ).all()
    )
    rows = await db.execute(
        select(AuditLog, User)
        .outerjoin(User, User.id == AuditLog.user_id)
        .where(
            AuditLog.institution_id == user.institution_id,
            or_(
                and_(
                    AuditLog.entity_type == Release.__tablename__,
                    AuditLog.entity_id == release.id,
                ),
                and_(
                    AuditLog.entity_type == Reading.__tablename__,
                    AuditLog.entity_id.in_(list(measure_keys)),
                    AuditLog.field.in_(_READING_HISTORY_FIELDS),
                ),
            ),
        )
        .order_by(AuditLog.created_at.desc(), AuditLog.id)
        .limit(limit)
    )
    entries = rows.all()
    researcher_ids = {
        UUID(value)
        for entry, _ in entries
        if entry.field == "researcher_id"
        for value in (entry.old_value, entry.new_value)
        if value
    }
    names = (
        dict(
            (
                await db.execute(
                    select(Researcher.id, Researcher.name).where(Researcher.id.in_(researcher_ids))
                )
            ).all()
        )
        if researcher_ids
        else {}
    )

    def label(entry: AuditLog, value: Any) -> str | None:
        return names.get(UUID(value)) if value and entry.field == "researcher_id" else None

    return [
        HistoryEntry(
            at=entry.created_at,
            action=entry.action,
            entity="release" if entry.entity_type == Release.__tablename__ else "reading",
            measure_key=measure_keys.get(entry.entity_id),
            field=entry.field,
            old_value=entry.old_value,
            new_value=entry.new_value,
            old_label=label(entry, entry.old_value),
            new_label=label(entry, entry.new_value),
            user_id=entry.user_id,
            user_name=(person.full_name or person.email) if person else None,
            user_active=person.is_active if person else None,
        )
        for entry, person in entries
    ]
