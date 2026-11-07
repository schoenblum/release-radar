"""The researcher directory: search, edit, merge (BRIEF section 6.3).

Reachable by editors as well as admins. Viewers can read it. A merged record stays as a
pointer to the survivor, so older history still leads to a person (R6.3.2).
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import ColumnElement, Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.database import get_db
from app.deps import get_current_user, require_editor
from app.models import Release, Researcher, Unit, User
from app.schemas.settings import (
    MergedRecord,
    MergeResearchers,
    ResearcherCreate,
    ResearcherDetail,
    ResearcherOut,
    ResearcherPage,
    ResearcherRelease,
    SplitResearcher,
    SplitResult,
    UnmergeResult,
)
from app.services import field_patch
from app.services.audit import to_json
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

router = APIRouter(prefix="/researchers", tags=["researchers"])

SPECS: dict[str, FieldSpec] = {
    "name": field_patch.text(required=True),
    "given_name": field_patch.text(),
    "family_name": field_patch.text(),
    "name_ja": field_patch.text(),
    "current_unit_id": field_patch.reference(Unit),
    "gender": field_patch.choice("M", "F", "other", "not_recorded"),
    "researchmap_id": field_patch.text(),
    "orcid": field_patch.text(32),
    "status": field_patch.choice("incomplete", "unverified", "verified"),
    "notes": field_patch.text(5000),
}
# What a merge copies to the survivor where the survivor has nothing.
_FILLED_ON_MERGE = (
    "given_name",
    "family_name",
    "name_ja",
    "current_unit_id",
    "researchmap_id",
    "orcid",
    "notes",
)


def _normalised_name(column: InstrumentedAttribute) -> ColumnElement:
    """Case and spacing aside, the same name. Never used to decide who is who (R6.3.1)."""
    return func.lower(func.btrim(func.regexp_replace(column, r"\s+", " ", "g")))


def _directory(institution_id: UUID) -> tuple[Select, ColumnElement, ColumnElement]:
    """Each record with its counts, the institution's condition, and how many share its name."""
    releases = (
        select(Release.researcher_id, func.count().label("total"))
        .where(Release.institution_id == institution_id, Release.deleted_at.is_(None))
        .group_by(Release.researcher_id)
        .subquery()
    )
    merged = (
        select(Researcher.merged_into_id, func.count().label("total"))
        .where(Researcher.institution_id == institution_id, Researcher.merged_into_id.is_not(None))
        .group_by(Researcher.merged_into_id)
        .subquery()
    )
    names = (
        # Grouped by label. In Postgres a bare "name" would mean the column, not the result.
        select(_normalised_name(Researcher.name).label("normal_name"), func.count().label("total"))
        .where(Researcher.institution_id == institution_id, Researcher.merged_into_id.is_(None))
        .group_by("normal_name")
        .subquery()
    )
    statement = (
        select(
            Researcher,
            func.coalesce(releases.c.total, 0),
            func.coalesce(names.c.total, 1) - 1,
            func.coalesce(merged.c.total, 0),
        )
        .outerjoin(releases, releases.c.researcher_id == Researcher.id)
        .outerjoin(merged, merged.c.merged_into_id == Researcher.id)
        .outerjoin(names, names.c.normal_name == _normalised_name(Researcher.name))
    )
    return statement, Researcher.institution_id == institution_id, names.c.total


def _out(
    researcher: Researcher, release_count: int, same_name_count: int, merged_count: int
) -> ResearcherOut:
    out = ResearcherOut.model_validate(researcher)
    out.release_count = release_count
    out.same_name_count = same_name_count
    out.merged_count = merged_count
    return out


async def _current(db: AsyncSession, researcher: Researcher) -> ResearcherOut:
    """A record as the directory shows it, after a change to it."""
    statement, in_institution, _ = _directory(researcher.institution_id)
    row = (await db.execute(statement.where(in_institution, Researcher.id == researcher.id))).one()
    return _out(*row)


@router.get("", response_model=ResearcherPage)
async def list_researchers(
    search: str | None = Query(default=None, max_length=255),
    status_filter: str | None = Query(default=None, alias="status"),
    same_name: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResearcherPage:
    statement, in_institution, name_total = _directory(user.institution_id)
    conditions = [in_institution, Researcher.merged_into_id.is_(None)]
    if status_filter:
        conditions.append(Researcher.status == status_filter)
    if same_name:
        conditions.append(name_total > 1)
    if search and search.strip():
        term = search.strip()
        conditions.append(
            or_(
                *(
                    column.icontains(term, autoescape=True)
                    for column in (
                        Researcher.name,
                        Researcher.given_name,
                        Researcher.family_name,
                        Researcher.name_ja,
                        Researcher.orcid,
                        Researcher.researchmap_id,
                        Researcher.notes,
                    )
                )
            )
        )
    filtered = statement.where(*conditions)
    total = await db.scalar(select(func.count()).select_from(filtered.subquery()))
    rows = await db.execute(
        filtered.order_by(func.lower(Researcher.name), Researcher.id).limit(limit).offset(offset)
    )
    return ResearcherPage(items=[_out(*row) for row in rows.all()], total=total or 0)


@router.get("/{researcher_id}", response_model=ResearcherDetail)
async def get_researcher(
    researcher_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResearcherDetail:
    """A record with what tells it apart: its releases, and what was merged into it."""
    statement, in_institution, _ = _directory(user.institution_id)
    row = (
        await db.execute(statement.where(in_institution, Researcher.id == researcher_id))
    ).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
    detail = ResearcherDetail.model_validate(_out(*row).model_dump())
    releases = await db.scalars(
        select(Release)
        .where(Release.researcher_id == researcher_id, Release.deleted_at.is_(None))
        .order_by(Release.release_date.desc().nulls_first(), Release.created_at.desc())
    )
    detail.releases = [ResearcherRelease.model_validate(release) for release in releases]
    merged = await db.scalars(
        select(Researcher)
        .where(Researcher.merged_into_id == researcher_id)
        .order_by(Researcher.updated_at.desc())
    )
    detail.merged_records = [
        MergedRecord(
            id=record.id,
            name=record.name,
            updated_at=record.updated_at,
            release_count=len((record.merge_details or {}).get("release_ids", [])),
        )
        for record in merged
    ]
    return detail


@router.post("", response_model=ResearcherOut, status_code=status.HTTP_201_CREATED)
async def create_researcher(
    payload: ResearcherCreate,
    user: User = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
) -> ResearcherOut:
    values = {
        field: await clean_value(db, user.institution_id, SPECS[field], value)
        for field, value in payload.model_dump().items()
    }
    researcher = Researcher(institution_id=user.institution_id, **values)
    db.add(researcher)
    await commit_unique(db)
    return await _current(db, researcher)


@router.patch("/{researcher_id}")
async def patch_researcher(
    researcher_id: UUID,
    patch: FieldPatch,
    user: User = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    researcher = await load_for_update(db, Researcher, researcher_id, user.institution_id)
    if researcher.merged_into_id is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="researcher_merged")
    version = await patch_field(db, researcher, SPECS, patch, user.institution_id)
    await commit_unique(db)
    return patch_result(patch.field, getattr(researcher, patch.field), version)


async def _lock_records(
    db: AsyncSession, institution_id: UUID, *researcher_ids: UUID
) -> dict[UUID, Researcher]:
    """Locked in a fixed order, so two opposite actions cannot deadlock."""
    return {
        row.id: row
        for row in await db.scalars(
            select(Researcher)
            .where(Researcher.id.in_(researcher_ids), Researcher.institution_id == institution_id)
            .order_by(Researcher.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    }


@router.delete("/{researcher_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_empty_researcher(
    researcher_id: UUID,
    user: User = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Only a record nothing refers to, such as one a split just made and its Undo emptied.

    Anything with a release, even a removed one, or with a record merged into it stays. The
    audit log keeps a copy of what was removed.
    """
    researcher = await load_for_update(db, Researcher, researcher_id, user.institution_id)
    in_use = await db.scalar(
        select(func.count()).select_from(Release).where(Release.researcher_id == researcher.id)
    ) or await db.scalar(
        select(func.count())
        .select_from(Researcher)
        .where(Researcher.merged_into_id == researcher.id)
    )
    if in_use or researcher.merged_into_id is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="researcher_in_use")
    await db.delete(researcher)
    await commit_unique(db)


@router.post("/{researcher_id}/merge", response_model=ResearcherOut)
async def merge_researcher(
    researcher_id: UUID,
    payload: MergeResearchers,
    user: User = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
) -> ResearcherOut:
    """Move this record's releases to the survivor. Every moved release is audit-logged."""
    if payload.into_id == researcher_id:
        raise field_error("merge_into_self")
    rows = await _lock_records(db, user.institution_id, researcher_id, payload.into_id)
    source, survivor = rows.get(researcher_id), rows.get(payload.into_id)
    if source is None or survivor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
    if source.merged_into_id is not None or survivor.merged_into_id is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="researcher_merged")

    releases = list(await db.scalars(select(Release).where(Release.researcher_id == source.id)))
    for release in releases:
        set_versioned(release, "researcher_id", survivor.id)
    filled: dict[str, Any] = {}
    for field in _FILLED_ON_MERGE:
        if getattr(survivor, field) is None and getattr(source, field) is not None:
            set_versioned(survivor, field, getattr(source, field))
            filled[field] = to_json(getattr(source, field))
    if survivor.gender == "not_recorded" and source.gender != "not_recorded":
        set_versioned(survivor, "gender", source.gender)
        filled["gender"] = source.gender

    # Records merged into this one earlier now lead straight to the survivor.
    for earlier in await db.scalars(
        select(Researcher).where(Researcher.merged_into_id == source.id)
    ):
        earlier.merged_into_id = survivor.id
    source.merged_into_id = survivor.id
    source.merge_details = {
        "release_ids": [str(release.id) for release in releases],
        "filled": filled,
    }
    await commit_unique(db)
    return await _current(db, survivor)


@router.post("/{researcher_id}/unmerge", response_model=UnmergeResult)
async def unmerge_researcher(
    researcher_id: UUID,
    user: User = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
) -> UnmergeResult:
    """Bring a merged record back, as it was merged in error (R6.3.2).

    Its releases return unless someone has moved them since, and what the merge filled in on
    the survivor is cleared unless someone has changed it since.
    """
    survivor_id = await db.scalar(
        select(Researcher.merged_into_id).where(
            Researcher.id == researcher_id, Researcher.institution_id == user.institution_id
        )
    )
    if survivor_id is None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="researcher_not_merged")
    rows = await _lock_records(db, user.institution_id, researcher_id, survivor_id)
    source, survivor = rows.get(researcher_id), rows.get(survivor_id)
    if source is None or survivor is None or source.merged_into_id != survivor_id:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="researcher_not_merged")

    details = source.merge_details or {}
    moved = await db.scalars(
        select(Release).where(
            Release.id.in_([UUID(release_id) for release_id in details.get("release_ids", [])]),
            Release.researcher_id == survivor.id,
        )
    )
    for release in moved:
        set_versioned(release, "researcher_id", source.id)
    for field, value in details.get("filled", {}).items():
        if to_json(getattr(survivor, field)) == value:
            set_versioned(survivor, field, "not_recorded" if field == "gender" else None)
    source.merged_into_id = None
    source.merge_details = None
    await commit_unique(db)
    return UnmergeResult(restored=await _current(db, source), survivor=await _current(db, survivor))


@router.post("/{researcher_id}/split", response_model=SplitResult)
async def split_researcher(
    researcher_id: UUID,
    payload: SplitResearcher,
    user: User = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
) -> SplitResult:
    """Move some releases to another record, for when one record covers two people (R6.3.2).

    With no target named, a new record takes them. It starts with the same name, since that
    is usually how the two came to be one, and marked incomplete, for someone to tell apart.
    """
    if payload.into_id == researcher_id:
        raise field_error("split_into_self")
    institution_id = user.institution_id
    ids = [researcher_id] + ([payload.into_id] if payload.into_id else [])
    rows = await _lock_records(db, institution_id, *ids)
    source = rows.get(researcher_id)
    target = rows.get(payload.into_id) if payload.into_id else None
    if source is None or (payload.into_id and target is None):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
    if source.merged_into_id is not None or (target and target.merged_into_id is not None):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="researcher_merged")

    releases = list(
        await db.scalars(
            select(Release).where(
                Release.id.in_(payload.release_ids), Release.researcher_id == source.id
            )
        )
    )
    if len(releases) != len(set(payload.release_ids)):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="release_moved")

    created = target is None
    if target is None:
        name = await clean_value(db, institution_id, SPECS["name"], payload.name or source.name)
        same_name = name == source.name
        target = Researcher(
            institution_id=institution_id,
            name=name,
            given_name=source.given_name if same_name else None,
            family_name=source.family_name if same_name else None,
            name_ja=source.name_ja if same_name else None,
            current_unit_id=source.current_unit_id,
            notes=await clean_value(db, institution_id, SPECS["notes"], payload.notes),
        )
        db.add(target)
        await db.flush()
    for release in releases:
        set_versioned(release, "researcher_id", target.id)
    await commit_unique(db)
    return SplitResult(
        source=await _current(db, source), target=await _current(db, target), created=created
    )
