"""Built-in checkpoints, measures and core-field settings (BRIEF sections 6.5, 6.6).

Seeding adds only what is absent, so it can run at every start without undoing what an
admin has changed. Labels come from the message catalogue, so the JA drafts are tracked
for review like all others. Lists and personal fields hold real names and are therefore
loaded by the importer (step 1.8), not here.
"""

from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.i18n import t
from app.models import Checkpoint, CoreFieldConfig, Institution, Measure


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

# In their default order on forms.
CORE_FIELDS = (
    "code",
    "title",
    "title_ja",
    "writer",
    "researcher",
    "also_featured",
    "unit",
    "field",
    "doi",
    # Next to the DOI: when the paper came out decides how soon a release is needed.
    "publication_date",
    "journal",
    "paper_title",
    "authors",
    "embargoed",
    "release_date",
    "release_time_et",
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
