"""Built-in checkpoints, measures, release types and core-field settings (BRIEF 6.4–6.6).

Seeding adds only what is absent, so it can run at every start without undoing what an
admin has changed. Labels come from the message catalogue, so the JA drafts are tracked
for review like all others. Lists and personal fields hold real names and are therefore
loaded by the importer (step 1.8), not here.
"""

from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.i18n import t
from app.models import (
    Checkpoint,
    CoreFieldConfig,
    Institution,
    Measure,
    ReleaseType,
    ScoreProfile,
    ScoreProfileVersion,
)
from app.models.score_profile import SEEDED_KEY


class MeasureSeed(NamedTuple):
    key: str
    metric: str
    checkpoint: str | None
    source: str
    applicability: str
    unit: str
    # Pickups exist only from Phase 4. Inactive until then, they count as not
    # applicable, so the default score profile works before they do (R8.2.4, R10.10).
    is_active: bool = True


CHECKPOINTS = (("d0", 0), ("d28", 28))

MEASURES = (
    MeasureSeed("ea_views.d0", "ea_views", "d0", "manual", "embargoed", "views"),
    MeasureSeed("ea_views.d28", "ea_views", "d28", "manual", "has_ea_url", "views"),
    MeasureSeed("altmetric.d0", "altmetric", "d0", "manual", "has_doi", "score"),
    MeasureSeed("altmetric.d28", "altmetric", "d28", "manual", "has_doi", "score"),
    MeasureSeed("hp_views.d28", "hp_views", "d28", "ga4", "website_on_domain", "views"),
    MeasureSeed("pickups_all", "pickups_all", None, "derived", "always", "count", False),
    MeasureSeed("pickups_major", "pickups_major", None, "derived", "always", "count", False),
)

# EurekAlert's categories, in its order (R6.4.1; www.eurekalert.org/releaseguidelines,
# checked 2026-11-09), each with EurekAlert's own wording as an alias, so a paste of it works.
RELEASE_TYPES = (
    ("peer_reviewed", ("Peer-reviewed publications", "Peer-reviewed", "Paper")),
    ("reports_proceedings", ("Reports and proceedings", "Report", "Proceedings")),
    ("business", ("Business announcements", "Business")),
    ("meeting", ("Meeting announcements", "Meeting")),
    ("grant_award", ("Grant and award announcements", "Grant", "Award")),
    ("book", ("Book announcements", "Book")),
    ("multimedia", ("Multimedia",)),
    ("media_advisory", ("Advisory",)),
    ("feature", ("Feature stories", "Feature")),
    ("article_highlight", ("Article highlights",)),
    ("press_summary", ("Press summaries",)),
)
# New and imported releases start as this, until an admin chooses another or none (R6.4.1).
DEFAULT_RELEASE_TYPE = "peer_reviewed"

# The default score profile, "News performance" (BRIEF §8.2, Daniel's ordering in the intake's
# Score weights). Pickups carry 45 % and are not applicable until Phase 4 collects them (R8.2.4).
DEFAULT_PROFILE_WEIGHTS = {
    "pickups_major": 35,
    "altmetric": 25,
    "ea_views.d28": 15,
    "ea_views.d0": 10,
    "pickups_all": 10,
    "hp_views.d28": 5,
}

# In their default order on forms.
CORE_FIELDS = (
    "code",
    "title",
    "title_ja",
    "writer",
    "researcher",
    # The researcher's, shown next to them; counts whom releases reach.
    "researcher_gender",
    "also_featured",
    "unit",
    "field",
    # What kind of release: types stay apart in analysis (R6.4.1).
    "release_type",
    "doi",
    # Next to the DOI: when the paper came out decides how soon a release is needed.
    "publication_date",
    "journal",
    "paper_title",
    "authors",
    "embargoed",
    "release_date",
    "release_time",
    "ea_url",
    "website_url",
    "ea_top_page",
    "ea_top_position",
    "notes",
)
# R5.4.4: the optional Japanese title is hidden by default.
HIDDEN_BY_DEFAULT = frozenset({"title_ja"})


def _label_key(key: str) -> str:
    return key.replace(".", "_")


async def seed_defaults(db: AsyncSession, institution: Institution) -> None:
    """Add the built-ins that are absent. The caller commits."""
    institution_id = institution.id

    checkpoints = {
        checkpoint.key: checkpoint
        for checkpoint in await db.scalars(
            select(Checkpoint).where(Checkpoint.institution_id == institution_id)
        )
    }
    for key, offset_days in CHECKPOINTS:
        if key not in checkpoints:
            checkpoint = Checkpoint(
                institution_id=institution_id,
                key=key,
                label_en=t("en", f"seed.checkpoint.{key}"),
                label_ja=t("ja", f"seed.checkpoint.{key}"),
                offset_days=offset_days,
            )
            db.add(checkpoint)
            checkpoints[key] = checkpoint
    await db.flush()

    measure_keys = set(
        await db.scalars(select(Measure.key).where(Measure.institution_id == institution_id))
    )
    for position, seed in enumerate(MEASURES):
        if seed.key not in measure_keys:
            db.add(
                Measure(
                    institution_id=institution_id,
                    key=seed.key,
                    metric=seed.metric,
                    checkpoint_id=checkpoints[seed.checkpoint].id if seed.checkpoint else None,
                    source=seed.source,
                    applicability=seed.applicability,
                    unit=seed.unit,
                    label_en=t("en", f"seed.measure.{_label_key(seed.key)}"),
                    label_ja=t("ja", f"seed.measure.{_label_key(seed.key)}"),
                    position=position,
                    is_active=seed.is_active,
                )
            )

    type_keys = set(
        await db.scalars(
            select(ReleaseType.key).where(ReleaseType.institution_id == institution_id)
        )
    )
    for position, (key, aliases) in enumerate(RELEASE_TYPES):
        if key in type_keys:
            continue
        release_type = ReleaseType(
            institution_id=institution_id,
            key=key,
            name_en=t("en", f"seed.release_type.{key}"),
            name_ja=t("ja", f"seed.release_type.{key}"),
            aliases=list(aliases),
            position=position,
        )
        db.add(release_type)
        # Only when the default type is first made: an admin's later choice of none stays.
        if key == DEFAULT_RELEASE_TYPE and institution.default_release_type_id is None:
            await db.flush()
            institution.default_release_type_id = release_type.id

    # Where the Analysis filters start: peer-reviewed publications (R6.4.2, R8.4.1). Only while
    # unset, so an admin's later choice stays.
    if institution.analysed_release_type_ids is None or institution.shown_release_type_ids is None:
        await db.flush()
        peer = await db.scalar(
            select(ReleaseType.id).where(
                ReleaseType.institution_id == institution_id,
                ReleaseType.key == DEFAULT_RELEASE_TYPE,
            )
        )
        start = [str(peer)] if peer else []
        if institution.analysed_release_type_ids is None:
            institution.analysed_release_type_ids = start
        if institution.shown_release_type_ids is None:
            institution.shown_release_type_ids = start

    await _seed_profile(db, institution_id)

    core_keys = set(
        await db.scalars(
            select(CoreFieldConfig.key).where(CoreFieldConfig.institution_id == institution_id)
        )
    )
    for position, key in enumerate(CORE_FIELDS):
        if key not in core_keys:
            db.add(
                CoreFieldConfig(
                    institution_id=institution_id,
                    key=key,
                    hidden=key in HIDDEN_BY_DEFAULT,
                    position=position,
                )
            )
    await db.flush()


async def _seed_profile(db: AsyncSession, institution_id) -> None:
    """The default score profile, once. Defaults are filled in, so a fresh install needs no
    configuration (R8.2.5)."""
    exists = await db.scalar(
        select(ScoreProfile.id).where(
            ScoreProfile.institution_id == institution_id, ScoreProfile.key == SEEDED_KEY
        )
    )
    if exists is not None:
        return
    has_default = await db.scalar(
        select(ScoreProfile.id).where(
            ScoreProfile.institution_id == institution_id, ScoreProfile.is_default.is_(True)
        )
    )
    profile = ScoreProfile(
        institution_id=institution_id,
        key=SEEDED_KEY,
        is_default=has_default is None,
        seeded=True,
    )
    db.add(profile)
    await db.flush()
    db.add(
        ScoreProfileVersion(
            institution_id=institution_id,
            profile_id=profile.id,
            version=1,
            name_en=t("en", "seed.profile.name"),
            name_ja=t("ja", "seed.profile.name"),
            purpose=t("en", "seed.profile.purpose"),
            weights=dict(DEFAULT_PROFILE_WEIGHTS),
            altmetric_basis="increase",
            coverage_min=60,
            comparison_years=3,
            min_values=10,
        )
    )
