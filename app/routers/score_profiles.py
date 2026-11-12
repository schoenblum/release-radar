"""Score profiles (R8.2, phase-2 brief §4.3): read by everyone signed in (the Analysis pages
offer them), changed by admins in Settings → Score profiles.

Every save is a new version; versions are never changed, so a report can cite the one its
scores came from. The preview shows the current top 5 under the saved and the edited version,
with the institution's default analysis filters.
"""

import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user, require_admin
from app.models import Institution, ScoreProfile, ScoreProfileVersion, User
from app.services.analysis import dataset as analysis
from app.services.analysis.profiles import components, default_filters, spec_of, weight_problem
from app.services.analysis.scoring import ProfileSpec, score_releases, top
from app.services.field_patch import field_error
from app.services.readings import today_in

router = APIRouter(prefix="/score-profiles", tags=["score profiles"])


class VersionIn(BaseModel):
    name_en: str = Field(min_length=1, max_length=255)
    name_ja: str | None = Field(default=None, max_length=255)
    purpose: str | None = Field(default=None, max_length=2000)
    weights: dict[str, int]
    altmetric_basis: Literal["increase", "d28"] = "increase"
    coverage_min: int = Field(default=60, ge=0, le=100)
    comparison_years: int = Field(default=3, ge=1, le=10)
    min_values: int = Field(default=10, ge=1, le=1000)


class VersionOut(BaseModel):
    id: uuid.UUID
    version: int
    name_en: str
    name_ja: str | None
    purpose: str | None
    weights: dict[str, int]
    altmetric_basis: str
    coverage_min: int
    comparison_years: int
    min_values: int
    created_at: datetime
    created_by: str | None


class ProfileOut(BaseModel):
    id: uuid.UUID
    key: str | None
    is_default: bool
    seeded: bool
    current: VersionOut
    versions: list[VersionOut] = []


class ComponentOut(BaseModel):
    key: str
    label_en: str
    label_ja: str
    allowed_in_default: bool


class PreviewIn(BaseModel):
    version: VersionIn
    # The profile being edited, to compare with its saved version.
    profile_id: uuid.UUID | None = None


class PreviewRow(BaseModel):
    release_id: uuid.UUID
    code: str | None
    title: str | None
    score: int
    coverage: float
    components: list[str]


class PreviewOut(BaseModel):
    edited: list[PreviewRow]
    saved: list[PreviewRow] | None
    saved_version: int | None


async def _versions(
    db: AsyncSession, profile_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[VersionOut]]:
    rows = await db.execute(
        select(ScoreProfileVersion, User.full_name, User.email)
        .outerjoin(User, User.id == ScoreProfileVersion.created_by_id)
        .where(ScoreProfileVersion.profile_id.in_(profile_ids))
        .order_by(ScoreProfileVersion.version.desc())
    )
    found: dict[uuid.UUID, list[VersionOut]] = {key: [] for key in profile_ids}
    for version, full_name, email in rows.all():
        found[version.profile_id].append(
            VersionOut(
                id=version.id,
                version=version.version,
                name_en=version.name_en,
                name_ja=version.name_ja,
                purpose=version.purpose,
                weights=version.weights,
                altmetric_basis=version.altmetric_basis,
                coverage_min=version.coverage_min,
                comparison_years=version.comparison_years,
                min_values=version.min_values,
                created_at=version.created_at,
                created_by=full_name or email,
            )
        )
    return found


async def _out(
    db: AsyncSession, profiles: list[ScoreProfile], *, history: bool
) -> list[ProfileOut]:
    versions = await _versions(db, [profile.id for profile in profiles])
    return [
        ProfileOut(
            id=profile.id,
            key=profile.key,
            is_default=profile.is_default,
            seeded=profile.seeded,
            current=versions[profile.id][0],
            versions=versions[profile.id] if history else [],
        )
        for profile in profiles
        if versions[profile.id]
    ]


async def _load(db: AsyncSession, profile_id: uuid.UUID, institution_id: uuid.UUID) -> ScoreProfile:
    profile = await db.scalar(
        select(ScoreProfile)
        .where(ScoreProfile.id == profile_id, ScoreProfile.institution_id == institution_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
    return profile


async def _check(db: AsyncSession, institution_id: uuid.UUID, body: VersionIn, *, seeded: bool):
    known = {
        item.key
        for item in components(
            analysis.dimensions_of(await analysis.measures_of(db, institution_id))
        )
    }
    weights = {key: weight for key, weight in body.weights.items() if weight}
    problem = weight_problem(weights, known, seeded=seeded)
    if problem:
        raise field_error(problem)
    return weights


def _version(
    profile: ScoreProfile, number: int, body: VersionIn, weights: dict
) -> ScoreProfileVersion:
    return ScoreProfileVersion(
        institution_id=profile.institution_id,
        profile_id=profile.id,
        version=number,
        name_en=body.name_en.strip(),
        name_ja=(body.name_ja or "").strip() or None,
        purpose=(body.purpose or "").strip() or None,
        weights=weights,
        altmetric_basis=body.altmetric_basis,
        coverage_min=body.coverage_min,
        comparison_years=body.comparison_years,
        min_values=body.min_values,
    )


@router.get("", response_model=list[ProfileOut])
async def list_profiles(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[ProfileOut]:
    profiles = list(
        await db.scalars(
            select(ScoreProfile)
            .where(ScoreProfile.institution_id == user.institution_id)
            .order_by(ScoreProfile.is_default.desc(), ScoreProfile.created_at)
        )
    )
    return await _out(db, profiles, history=False)


@router.get("/components", response_model=list[ComponentOut])
async def list_components(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[ComponentOut]:
    dimensions = analysis.dimensions_of(await analysis.measures_of(db, user.institution_id))
    return [
        ComponentOut(
            key=item.key,
            label_en=item.label_en,
            label_ja=item.label_ja,
            allowed_in_default=item.allowed_in_seeded,
        )
        for item in components(dimensions)
    ]


@router.get("/{profile_id}", response_model=ProfileOut)
async def get_profile(
    profile_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileOut:
    profile = await db.scalar(
        select(ScoreProfile).where(
            ScoreProfile.id == profile_id, ScoreProfile.institution_id == user.institution_id
        )
    )
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
    return (await _out(db, [profile], history=True))[0]


@router.post("", response_model=ProfileOut, status_code=status.HTTP_201_CREATED)
async def create_profile(
    body: VersionIn, admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)
) -> ProfileOut:
    """A new profile, from scratch or a copy the page filled in. Never the default at first."""
    weights = await _check(db, admin.institution_id, body, seeded=False)
    profile = ScoreProfile(institution_id=admin.institution_id, is_default=False, seeded=False)
    db.add(profile)
    await db.flush()
    db.add(_version(profile, 1, body, weights))
    await db.commit()
    return (await _out(db, [profile], history=True))[0]


@router.post("/{profile_id}/versions", response_model=ProfileOut)
async def save_version(
    profile_id: uuid.UUID,
    body: VersionIn,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ProfileOut:
    """Saving makes the next version; the ones before stay as they were."""
    profile = await _load(db, profile_id, admin.institution_id)
    weights = await _check(db, admin.institution_id, body, seeded=profile.seeded)
    latest = await db.scalar(
        select(func.max(ScoreProfileVersion.version)).where(
            ScoreProfileVersion.profile_id == profile.id
        )
    )
    db.add(_version(profile, (latest or 0) + 1, body, weights))
    await db.commit()
    return (await _out(db, [profile], history=True))[0]


@router.post("/{profile_id}/default", response_model=list[ProfileOut])
async def make_default(
    profile_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[ProfileOut]:
    profile = await _load(db, profile_id, admin.institution_id)
    if not profile.is_default:
        others = list(
            await db.scalars(
                select(ScoreProfile)
                .where(
                    ScoreProfile.institution_id == admin.institution_id,
                    ScoreProfile.is_default.is_(True),
                )
                .with_for_update()
            )
        )
        for other in others:
            other.is_default = False
        # The old default goes first, or the unique index would see two at once.
        await db.flush()
        profile.is_default = True
        await db.commit()
    return await list_profiles(admin, db)


def _rows(dataset: analysis.Dataset, spec: ProfileSpec, analysed, shown) -> list[PreviewRow]:
    scores = score_releases(dataset, spec, analysed)
    return [
        PreviewRow(
            release_id=row.id,
            code=row.code,
            title=row.title,
            score=score.value,
            coverage=score.coverage,
            components=score.components,
        )
        for row, score in top(dataset, scores, shown)
    ]


@router.post("/preview", response_model=PreviewOut)
async def preview(
    body: PreviewIn, admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)
) -> Any:
    """The current top 5 under the edited and the saved version (R8.2.5)."""
    institution = await db.get(Institution, admin.institution_id)
    saved: ScoreProfileVersion | None = None
    seeded = False
    if body.profile_id is not None:
        profile = await db.scalar(
            select(ScoreProfile).where(
                ScoreProfile.id == body.profile_id,
                ScoreProfile.institution_id == institution.id,
            )
        )
        if profile is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
        seeded = profile.seeded
        saved = await db.scalar(
            select(ScoreProfileVersion)
            .where(ScoreProfileVersion.profile_id == profile.id)
            .order_by(ScoreProfileVersion.version.desc())
            .limit(1)
        )
    weights = await _check(db, institution.id, body.version, seeded=seeded)
    dataset = await analysis.load(db, institution, today_in(institution.timezone))
    analysed, shown = default_filters(institution)
    edited = ProfileSpec(
        weights=weights,
        altmetric_basis=body.version.altmetric_basis,
        coverage_min=body.version.coverage_min,
        comparison_years=body.version.comparison_years,
        min_values=body.version.min_values,
    )
    return PreviewOut(
        edited=_rows(dataset, edited, analysed, shown),
        saved=_rows(dataset, spec_of(saved), analysed, shown) if saved else None,
        saved_version=saved.version if saved else None,
    )


async def default_spec(db: AsyncSession, institution_id: uuid.UUID) -> ProfileSpec | None:
    """The default profile's current version, for the pages and positions of step 2.3."""
    version = await db.scalar(
        select(ScoreProfileVersion)
        .join(ScoreProfile, ScoreProfile.id == ScoreProfileVersion.profile_id)
        .where(ScoreProfile.institution_id == institution_id, ScoreProfile.is_default.is_(True))
        .order_by(ScoreProfileVersion.version.desc())
        .limit(1)
    )
    return spec_of(version) if version else None
