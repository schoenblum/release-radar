"""The researcher directory: search, edit, merge (BRIEF section 6.3).

Reachable by editors as well as admins. Viewers can read it. A merged record stays as a
pointer to the survivor, so older history still leads to a person (R6.3.2).
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user, require_editor
from app.models import Release, Researcher, Unit, User
from app.schemas.settings import (
    MergeResearchers,
    ResearcherCreate,
    ResearcherOut,
    ResearcherPage,
)
from app.services import field_patch
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


def _out(researcher: Researcher, release_count: int) -> ResearcherOut:
    out = ResearcherOut.model_validate(researcher)
    out.release_count = release_count
    return out


@router.get("", response_model=ResearcherPage)
async def list_researchers(
    search: str | None = Query(default=None, max_length=255),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResearcherPage:
    conditions = [
        Researcher.institution_id == user.institution_id,
        Researcher.merged_into_id.is_(None),
    ]
    if status_filter:
        conditions.append(Researcher.status == status_filter)
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
                    )
                )
            )
        )
    total = await db.scalar(select(func.count()).select_from(Researcher).where(*conditions))
    counts = (
        select(Release.researcher_id, func.count().label("releases"))
        .where(Release.institution_id == user.institution_id)
        .group_by(Release.researcher_id)
        .subquery()
    )
    rows = await db.execute(
        select(Researcher, func.coalesce(counts.c.releases, 0))
        .outerjoin(counts, counts.c.researcher_id == Researcher.id)
        .where(*conditions)
        .order_by(func.lower(Researcher.name), Researcher.id)
        .limit(limit)
        .offset(offset)
    )
    return ResearcherPage(items=[_out(row, count) for row, count in rows.all()], total=total or 0)


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
    return _out(researcher, 0)


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
    # Locked in a fixed order, so two opposite merges cannot deadlock.
    rows = {
        row.id: row
        for row in await db.scalars(
            select(Researcher)
            .where(
                Researcher.id.in_([researcher_id, payload.into_id]),
                Researcher.institution_id == user.institution_id,
            )
            .order_by(Researcher.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    }
    source, survivor = rows.get(researcher_id), rows.get(payload.into_id)
    if source is None or survivor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
    if source.merged_into_id is not None or survivor.merged_into_id is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="researcher_merged")

    releases = list(await db.scalars(select(Release).where(Release.researcher_id == source.id)))
    for release in releases:
        set_versioned(release, "researcher_id", survivor.id)
    for field in _FILLED_ON_MERGE:
        if getattr(survivor, field) is None and getattr(source, field) is not None:
            set_versioned(survivor, field, getattr(source, field))
    if survivor.gender == "not_recorded" and source.gender != "not_recorded":
        set_versioned(survivor, "gender", source.gender)

    # Records merged into this one earlier now lead straight to the survivor.
    for earlier in await db.scalars(
        select(Researcher).where(Researcher.merged_into_id == source.id)
    ):
        earlier.merged_into_id = survivor.id
    source.merged_into_id = survivor.id
    await commit_unique(db)

    count = await db.scalar(
        select(func.count()).select_from(Release).where(Release.researcher_id == survivor.id)
    )
    return _out(survivor, count or 0)
