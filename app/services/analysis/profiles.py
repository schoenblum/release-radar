"""Score profiles as the computation and the settings page need them (R8.2, phase-2 brief §4.3)."""

import uuid
from dataclasses import dataclass

from app.i18n import t
from app.models import Institution, ScoreProfileVersion
from app.services.analysis.dataset import ALTMETRIC_INCREASE, Dimension
from app.services.analysis.filters import AnalysisFilter
from app.services.analysis.scoring import ALTMETRIC, ProfileSpec

# Altmetric enters a profile once, as "altmetric", on the profile's basis (R8.2.2).
_RAW_ALTMETRIC = frozenset({"altmetric.d0", "altmetric.d28", ALTMETRIC_INCREASE})
# R8.2.3: other profiles may use these, the seeded default never.
NOT_IN_SEEDED = frozenset({"satisfaction", "research_outcomes"})


@dataclass(frozen=True)
class Component:
    key: str
    label_en: str
    label_ja: str
    allowed_in_seeded: bool


def components(dimensions: list[Dimension]) -> list[Component]:
    """What a profile can weigh: every dimension except scores and the raw Altmetric ones,
    which come in as one component instead."""
    found: list[Component] = []
    for dimension in dimensions:
        if dimension.kind == "score":
            continue
        if dimension.key in _RAW_ALTMETRIC:
            if not any(item.key == ALTMETRIC for item in found):
                found.append(
                    Component(
                        ALTMETRIC,
                        t("en", "analysis.dimensions.altmetric"),
                        t("ja", "analysis.dimensions.altmetric"),
                        True,
                    )
                )
            continue
        found.append(
            Component(
                dimension.key,
                dimension.label_en,
                dimension.label_ja,
                dimension.key not in NOT_IN_SEEDED,
            )
        )
    return found


def weight_problem(weights: dict[str, int], known: set[str], *, seeded: bool) -> str | None:
    """Why these weights cannot be saved, as an error code, or None."""
    for key, weight in weights.items():
        if key not in known:
            return "profile_component_unknown"
        if not 0 <= weight <= 100:
            return "field_out_of_range"
        if seeded and weight and key in NOT_IN_SEEDED:
            return "profile_component_not_in_default"
    if sum(weights.values()) != 100:
        return "profile_weights_total"
    return None


def spec_of(version: ScoreProfileVersion) -> ProfileSpec:
    return ProfileSpec(
        weights={key: int(weight) for key, weight in version.weights.items() if weight},
        altmetric_basis=version.altmetric_basis,
        coverage_min=version.coverage_min,
        comparison_years=version.comparison_years,
        min_values=version.min_values,
        profile_id=version.profile_id,
        version=version.version,
    )


def _types(ids: list | None) -> frozenset[uuid.UUID | None] | None:
    # Empty or unset: every type, so nothing is restricted.
    return frozenset(uuid.UUID(str(item)) for item in ids) if ids else None


def default_filters(institution: Institution) -> tuple[AnalysisFilter, AnalysisFilter]:
    """The institution's starting point for the two filters (R6.4.2): analysed, shown."""
    analysed = _types(institution.analysed_release_type_ids)
    shown = _types(institution.shown_release_type_ids)
    if analysed is not None and shown is not None:
        shown = shown & analysed or analysed
    return AnalysisFilter(release_types=analysed), AnalysisFilter(release_types=shown or analysed)
