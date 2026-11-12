"""Percentiles and scores (BRIEF §8.3, D14; phase-2 brief §4.2, made precise).

For a release r and a profile version p:

1. **Comparison set** S(r): the finished releases inside the analysis inclusion filter whose
   academic year is AY(r) or one of the N − 1 before it. A provisional r is ranked as if it were
   in S(r).
2. **Component percentile** P_i(r) = (number below + ½ × number equal) / n × 100 over the members
   of S(r) with a value for component i; r itself is among the "equal" and counted in n.
3. **Minimum values**: a component with fewer than ``min_values`` values (n) counts as missing.
4. **Weights**: not applicable components leave the weight base; coverage = weight with a
   percentile ÷ applicable weight; below the minimum coverage there is no score ("insufficient
   data"); otherwise score = Σ w_i P_i ÷ Σ w_i over the components with a percentile.
"""

import uuid
from collections import defaultdict
from dataclasses import dataclass, field

from app.services.analysis.dataset import ALTMETRIC_INCREASE, Dataset, Row
from app.services.analysis.filters import AnalysisFilter
from app.services.analysis.stats import mid_rank, whole
from app.services.readings import STATE_NOT_APPLICABLE

# The profile component that stands for Altmetric, read on the profile's basis (R8.2.2), so
# Altmetric cannot enter a profile twice.
ALTMETRIC = "altmetric"
BASIS_INCREASE = "increase"
BASIS_DAY28 = "d28"


@dataclass(frozen=True)
class ProfileSpec:
    """One version of a score profile, as the computation needs it."""

    weights: dict[str, int]
    altmetric_basis: str = BASIS_INCREASE
    coverage_min: int = 60
    comparison_years: int = 3
    min_values: int = 10
    profile_id: uuid.UUID | None = None
    version: int | None = None

    def dimension_of(self, component: str) -> str:
        if component != ALTMETRIC:
            return component
        return ALTMETRIC_INCREASE if self.altmetric_basis == BASIS_INCREASE else "altmetric.d28"


@dataclass
class Score:
    # 0–100 to show, without decimals; ``exact`` keeps the unrounded number.
    value: int | None
    exact: float | None
    coverage: float
    provisional: bool
    # The components the score is based on (R8.1.4), in the profile's order.
    components: list[str] = field(default_factory=list)
    percentiles: dict[str, float] = field(default_factory=dict)

    @property
    def insufficient(self) -> bool:
        return self.value is None


class Ranker:
    """Sorted values per academic year and dimension, so each percentile is two bisections."""

    def __init__(self, dataset: Dataset, analysed: AnalysisFilter, years: int) -> None:
        self.dataset = dataset
        self.analysed = analysed
        self.years = max(years, 1)
        self._finished: dict[int, list[Row]] = defaultdict(list)
        for row in dataset.rows:
            if row.finished and analysed.matches(row):
                self._finished[row.academic_year].append(row)
        self._cache: dict[tuple[int, str], list[float]] = {}

    def members(self, year: int) -> list[Row]:
        """S for a release of this academic year: its year and the N − 1 before it."""
        return [
            row
            for ay in range(year - self.years + 1, year + 1)
            for row in self._finished.get(ay, [])
        ]

    def values(self, year: int, key: str) -> list[float]:
        found = self._cache.get((year, key))
        if found is None:
            found = sorted(
                row.cell(key).value for row in self.members(year) if row.cell(key).has_value
            )
            self._cache[(year, key)] = found
        return found

    def percentile(self, row: Row, key: str) -> tuple[float, int] | None:
        """r's percentile for one dimension and n, or None when r has no value. Only for a
        release inside the analysed set: outside it there is nothing to compare with."""
        cell = row.cell(key)
        if not cell.has_value:
            return None
        in_set = row.finished and self.analysed.matches(row)
        return mid_rank(cell.value, self.values(row.academic_year, key), include_self=not in_set)


def score_release(row: Row, spec: ProfileSpec, ranker: Ranker) -> Score:
    applicable = covered = total = 0.0
    used: list[str] = []
    percentiles: dict[str, float] = {}
    for component, weight in spec.weights.items():
        if weight <= 0:
            continue
        key = spec.dimension_of(component)
        if row.cell(key).state == STATE_NOT_APPLICABLE:
            continue
        applicable += weight
        ranked = ranker.percentile(row, key)
        if ranked is None or ranked[1] < spec.min_values:
            continue
        covered += weight
        total += weight * ranked[0]
        used.append(component)
        percentiles[component] = ranked[0]
    coverage = covered / applicable if applicable else 0.0
    provisional = not row.finished
    if not applicable or coverage * 100 < spec.coverage_min:
        return Score(None, None, coverage, provisional, used, percentiles)
    exact = total / covered
    return Score(whole(exact), exact, coverage, provisional, used, percentiles)


def score_releases(
    dataset: Dataset, spec: ProfileSpec, analysed: AnalysisFilter
) -> dict[uuid.UUID, Score]:
    """A score for every release inside the analysed set, finished or provisional."""
    ranker = Ranker(dataset, analysed, spec.comparison_years)
    return {
        row.id: score_release(row, spec, ranker) for row in dataset.rows if analysed.matches(row)
    }


def top(
    dataset: Dataset,
    scores: dict[uuid.UUID, Score],
    shown: AnalysisFilter,
    count: int = 5,
    *,
    lowest: bool = False,
) -> list[tuple[Row, Score]]:
    """The highest (or lowest) finished, shown releases with a score. A provisional release or
    one with insufficient data never lands in the list (phase-2 brief §5.4)."""
    ranked = [
        (row, scores[row.id])
        for row in dataset.rows
        if row.id in scores
        and row.finished
        and shown.matches(row)
        and scores[row.id].exact is not None
    ]
    ranked.sort(key=lambda pair: (pair[1].exact, pair[0].release_date), reverse=not lowest)
    return ranked[:count]
