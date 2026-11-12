"""What the Analysis pages show (phase-2 brief §5): cards, rankings, top and bottom, positions.

Everything here works on one ``Dataset`` with the two filters and one profile version, so the
overview, a dimension's page, top and bottom, their exports and the Data page's positions always
agree.

- **The population** of a dimension is the analysed releases with a value; for the score, the
  analysed releases whose score is final (finished and enough data). Box, median, ranks and the
  count line describe it. The *shown* releases are its points and rows, and change none of it.
- **Rank** = 1 + the number of values in the population that are higher; ties share a rank. A
  release outside the population with a value (a provisional score) gets the rank it would have.
- **Percentile** is the one the score uses: within the release's comparison set (its academic
  year and the N − 1 before it), and only when that has at least the profile's minimum of values.
"""

import uuid
from bisect import bisect_right
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from app.i18n import t
from app.services.analysis.dataset import (
    ALTMETRIC_INCREASE,
    FEEDBACK_DIMENSIONS,
    Choice,
    Dataset,
    Dimension,
    Row,
)
from app.services.analysis.filters import AnalysisFilter
from app.services.analysis.scoring import (
    ALTMETRIC,
    BASIS_DAY28,
    BASIS_INCREASE,
    ProfileSpec,
    Ranker,
    Score,
    score_releases,
)
from app.services.analysis.stats import quantile_inc
from app.services.readings import (
    STATE_MISSING,
    STATE_NOT_APPLICABLE,
    STATE_NOT_YET_DUE,
    STATE_VALUE,
)

SCORE = "score"
# A score that exists but rests on too little data (below the profile's coverage minimum).
STATE_INSUFFICIENT = "insufficient"
# Altmetric is one card, read on a basis; its raw dimensions are not cards of their own.
_RAW_ALTMETRIC = frozenset({"altmetric.d0", "altmetric.d28", ALTMETRIC_INCREASE})
TOP_COUNT = 5


def altmetric_dimension(basis: str) -> str:
    return ALTMETRIC_INCREASE if basis == BASIS_INCREASE else "altmetric.d28"


def page_keys(dataset: Dataset) -> list[str]:
    """Every dimension with a page, in order: the score, Altmetric, then the rest as the read
    layer lists them. A dimension appears once any release has a value for it, so measures added
    later (pickups, the journal metric) get a card and a page without any change here.

    Researcher feedback has no page (Daniel, 2026-11-12: ranking releases by it is not how it
    is read); it shows as bars on the Overview, and its dimensions stay for score profiles."""
    with_data = {key for row in dataset.rows for key, cell in row.cells.items() if cell.has_value}
    keys = [SCORE]
    if with_data & {"altmetric.d28", ALTMETRIC_INCREASE}:
        keys.append(ALTMETRIC)
    keys += [
        item.key
        for item in dataset.dimensions
        if item.key not in _RAW_ALTMETRIC
        and item.key not in FEEDBACK_DIMENSIONS
        and item.kind != "score"
        and item.key in with_data
    ]
    return keys


# What a chart can be split by (Daniel, 2026-11-12): the filter dimensions, by the names the
# address uses. Never the writer (D9).
GROUPINGS = ("ay", "type", "field", "unit", "emb", "gender")
# Fewer values than this give a group its dots and median, but no box: a box of three says
# nothing a reader should trust.
MIN_BOX = 5


def group_of(row: Row, by: str) -> object:
    """A release's value on a grouping: its academic year, type, field, unit, embargo or
    researcher gender (None for no type, field or unit)."""
    if by == "ay":
        return row.academic_year
    if by == "type":
        return row.release_type_id
    if by == "field":
        return row.field_id
    if by == "unit":
        return row.unit_id
    if by == "emb":
        return row.embargoed
    if by == "gender":
        return row.gender
    raise KeyError(by)


def group_token(value: object) -> str:
    """A group's value as the address writes it: ``none``, ``1``/``0``, a year, an ID."""
    if value is None:
        return "none"
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value)


@dataclass(frozen=True)
class Box:
    """Excel's QUARTILE.INC of the population: lowest, quartiles, median, highest."""

    low: float
    q1: float
    median: float
    q3: float
    high: float
    n: int


def box_of(values: list[float]) -> Box | None:
    if not values:
        return None
    ordered = sorted(values)
    q = [quantile_inc(ordered, step / 4) for step in range(5)]
    return Box(q[0], q[1], q[2], q[3], q[4], len(ordered))


@dataclass
class Entry:
    """One release on a dimension: its value and state, and where it stands."""

    row: Row
    value: float | None
    state: str
    inferred: bool = False
    provisional: bool = False
    rank: int | None = None
    percentile: float | None = None
    # The score only: the unrounded score, which orders equal shown scores.
    exact: float | None = None
    coverage: float | None = None
    components: list[str] = field(default_factory=list)


@dataclass
class Counts:
    value: int = 0
    missing: int = 0
    not_applicable: int = 0
    not_yet_due: int = 0
    insufficient: int = 0
    provisional: int = 0


@dataclass
class Card:
    key: str
    # The read layer's dimension behind it: the Altmetric basis chosen, or "score".
    dimension: str
    label_en: str
    label_ja: str
    unit: str
    decimals: int
    box: Box | None
    counts: Counts
    # Shown releases in the population, as points.
    points: list[Entry]
    shown_median: float | None


@dataclass
class Group:
    """One group of a split chart: its box (None below ``MIN_BOX`` values), its median, and
    its shown releases as points. Like the card, the box describes the analysed releases."""

    value: object
    n: int
    median: float
    box: Box | None
    points: list[Entry]
    shown_median: float | None


@dataclass
class Analysis:
    """One request's worth: the dataset, both filters, the profile and the scores."""

    dataset: Dataset
    analysed: AnalysisFilter
    shown: AnalysisFilter
    spec: ProfileSpec | None
    altmetric_basis: str
    scores: dict[uuid.UUID, Score] = field(default_factory=dict)
    _ranker: Ranker | None = None

    def __post_init__(self) -> None:
        if self.spec is not None:
            self.scores = score_releases(self.dataset, self.spec, self.analysed)
        years = self.spec.comparison_years if self.spec else 3
        self._ranker = Ranker(self.dataset, self.analysed, years)

    @property
    def analysed_rows(self) -> list[Row]:
        return [row for row in self.dataset.rows if self.analysed.matches(row)]

    @property
    def shown_rows(self) -> list[Row]:
        return [
            row
            for row in self.dataset.rows
            if self.analysed.matches(row) and self.shown.matches(row)
        ]

    def dimension_key(self, key: str) -> str:
        if key == ALTMETRIC:
            return altmetric_dimension(self.altmetric_basis)
        return key

    def describe(self, key: str) -> Dimension:
        """Labels, unit and decimals of a page key."""
        if key == SCORE:
            return Dimension(
                SCORE,
                t("en", "analysis.dimensions.score"),
                t("ja", "analysis.dimensions.score"),
                "score",
                0,
                "score",
            )
        found = self.dataset.dimension(self.dimension_key(key))
        if found is None:
            raise KeyError(key)
        if key == ALTMETRIC:
            return Dimension(
                ALTMETRIC, found.label_en, found.label_ja, found.unit, found.decimals, "derived"
            )
        return found

    def _raw(self, row: Row, key: str) -> Entry:
        """A release's value and state on a page key, before ranking."""
        provisional = not row.finished
        if key == SCORE:
            score = self.scores.get(row.id)
            if score is None:
                return Entry(row, None, STATE_NOT_APPLICABLE, provisional=provisional)
            if score.value is None:
                return Entry(
                    row,
                    None,
                    STATE_INSUFFICIENT,
                    provisional=provisional,
                    coverage=score.coverage,
                    components=score.components,
                )
            return Entry(
                row,
                float(score.value),
                STATE_VALUE,
                provisional=provisional,
                exact=score.exact,
                coverage=score.coverage,
                components=score.components,
            )
        cell = row.cell(self.dimension_key(key))
        return Entry(
            row,
            cell.value if cell.has_value else None,
            cell.state,
            inferred=cell.inferred,
            provisional=provisional,
        )

    @staticmethod
    def _in_population(key: str, entry: Entry) -> bool:
        if entry.value is None:
            return False
        # A provisional score is not final, so it never sets the bar for others.
        return not (key == SCORE and entry.provisional)

    def entries(self, key: str) -> tuple[list[Entry], list[float]]:
        """Every analysed release on this key, ranked, and the population's values."""
        dimension = self.dimension_key(key)
        found = [self._raw(row, key) for row in self.analysed_rows]
        population = sorted(entry.value for entry in found if self._in_population(key, entry))
        for entry in found:
            if entry.value is None:
                continue
            entry.rank = 1 + len(population) - bisect_right(population, entry.value)
            if key == SCORE:
                continue
            ranked = self._ranker.percentile(entry.row, dimension)
            minimum = self.spec.min_values if self.spec else 1
            if ranked is not None and ranked[1] >= minimum:
                entry.percentile = ranked[0]
        return found, population

    def card(self, key: str) -> Card:
        described = self.describe(key)
        found, population = self.entries(key)
        counts = Counts()
        for entry in found:
            if key == SCORE and entry.provisional:
                counts.provisional += 1
            elif entry.state == STATE_VALUE:
                counts.value += 1
            elif entry.state == STATE_INSUFFICIENT:
                counts.insufficient += 1
            elif entry.state == STATE_MISSING:
                counts.missing += 1
            elif entry.state == STATE_NOT_YET_DUE:
                counts.not_yet_due += 1
            else:
                counts.not_applicable += 1
        points = [
            entry
            for entry in found
            if self._in_population(key, entry) and self.shown.matches(entry.row)
        ]
        shown_values = sorted(entry.value for entry in points)
        return Card(
            key=key,
            dimension=SCORE if key == SCORE else self.dimension_key(key),
            label_en=described.label_en,
            label_ja=described.label_ja,
            unit=described.unit,
            decimals=described.decimals,
            box=box_of(population),
            counts=counts,
            points=points,
            shown_median=quantile_inc(shown_values, 0.5),
        )

    def groups(self, key: str, by: str) -> list[Group]:
        """The card's population split by one grouping, each group with its own box: years,
        fields, units … side by side on the card's scale (Daniel, 2026-11-12). Only groups with
        a value appear, in the order of their values; the page orders them for reading."""
        found, _ = self.entries(key)
        members: dict[object, list[Entry]] = defaultdict(list)
        for entry in found:
            if self._in_population(key, entry):
                members[group_of(entry.row, by)].append(entry)
        groups = []
        for value, entries in sorted(members.items(), key=lambda item: group_token(item[0])):
            values = sorted(entry.value for entry in entries)
            points = [entry for entry in entries if self.shown.matches(entry.row)]
            shown_values = sorted(entry.value for entry in points)
            groups.append(
                Group(
                    value=value,
                    n=len(values),
                    median=quantile_inc(values, 0.5),
                    box=box_of(values) if len(values) >= MIN_BOX else None,
                    points=points,
                    shown_median=quantile_inc(shown_values, 0.5) if shown_values else None,
                )
            )
        return groups

    def rows(self, key: str) -> list[Entry]:
        """The shown releases on this key, best first, rows without a value last."""
        found, _ = self.entries(key)
        shown = [entry for entry in found if self.shown.matches(entry.row)]
        return sorted(shown, key=_ranked_order)

    def top_and_bottom(self, key: str, count: int = TOP_COUNT) -> tuple[list[Entry], list[Entry]]:
        """The highest and lowest finished, shown releases with a value (phase-2 brief §5.4).
        A provisional release or one with too little data for a score never lands in either,
        and no release is in both: with fewer than twice ``count``, the lowest list is shorter."""
        found, _ = self.entries(key)
        eligible = sorted(
            (
                entry
                for entry in found
                if entry.value is not None and entry.row.finished and self.shown.matches(entry.row)
            ),
            key=_ranked_order,
        )
        highest = eligible[:count]
        rest = eligible[len(highest) :]
        lowest = list(reversed(rest[-count:])) if rest else []
        return highest, lowest

    def year_medians(self, key: str = SCORE) -> list["YearMedian"]:
        """The median of each academic year's population: for the score over time."""
        found, _ = self.entries(key)
        by_year: dict[int, list[Entry]] = defaultdict(list)
        for entry in found:
            if self._in_population(key, entry):
                by_year[entry.row.academic_year].append(entry)
        medians = []
        for year, entries in sorted(by_year.items()):
            dates = [entry.row.release_date for entry in entries]
            values = sorted(entry.value for entry in entries)
            medians.append(
                YearMedian(year, quantile_inc(values, 0.5), len(values), min(dates), max(dates))
            )
        return medians

    def answer_chart(self, question: str, by: str | None = None) -> "AnswerChart | None":
        """How many of the shown releases' researchers ticked each box (Daniel, 2026-11-12:
        the bars follow both filters). Only releases whose researchers answered the question
        count. Split by a grouping, one bar per group; otherwise one bar for the shown releases
        and, when they are fewer than the analysed ones, one for those to compare with."""
        choices = [choice for choice in self.dataset.choices if choice.question == question]

        def answered(rows: list[Row]) -> list[Row]:
            return [row for row in rows if row.answers.get(question) is not None]

        shown = answered(self.shown_rows)
        series: list[tuple[str, list[Row]]]
        if by is not None:
            members: dict[object, list[Row]] = defaultdict(list)
            for row in shown:
                members[group_of(row, by)].append(row)
            series = [
                (group_token(value), rows)
                for value, rows in sorted(members.items(), key=lambda item: group_token(item[0]))
            ]
        else:
            series = [(SHOWN, shown)] if shown else []
            analysed = answered(self.analysed_rows)
            if len(analysed) != len(shown) and series:
                series.append((ANALYSED, analysed))
        if not choices or not series:
            return None
        bars = []
        for choice in choices:
            shares = []
            for key, rows in series:
                count = sum(1 for row in rows if choice.key in row.answers[question])
                shares.append(Share(key, count, 100 * count / len(rows)))
            bars.append(Bar(choice, shares))
        return AnswerChart(question, by, [(key, len(rows)) for key, rows in series], bars)

    def standings(
        self, keys: list[str]
    ) -> tuple[dict[str, float | None], list[tuple[Row, dict[str, "Standing"]]]]:
        """Each key's median over the analysed releases, and each shown release on each key
        against it: the All releases page (Daniel, 2026-11-12)."""
        per_key: dict[str, tuple[dict[uuid.UUID, Entry], float | None]] = {}
        for key in keys:
            found, population = self.entries(key)
            median = quantile_inc(population, 0.5) if population else None
            per_key[key] = ({entry.row.id: entry for entry in found}, median)
        table = []
        for row in self.shown_rows:
            line: dict[str, Standing] = {}
            for key, (entries, median) in per_key.items():
                entry = entries[row.id]
                difference = None
                if entry.value is not None and median:
                    difference = 100 * (entry.value - median) / median
                line[key] = Standing(entry, median, difference)
            table.append((row, line))
        return {key: median for key, (_, median) in per_key.items()}, table


@dataclass(frozen=True)
class YearMedian:
    year: int
    median: float
    n: int
    # The first and last release date among them, where the year's line starts and ends.
    first: date
    last: date


# The two bars of an unsplit survey chart.
SHOWN = "shown"
ANALYSED = "analysed"


@dataclass(frozen=True)
class Share:
    # Which bar: a group's token, or SHOWN or ANALYSED.
    series: str
    count: int
    # Of that bar's releases whose researchers answered, in per cent.
    share: float


@dataclass(frozen=True)
class Bar:
    choice: Choice
    shares: list[Share]


@dataclass(frozen=True)
class AnswerChart:
    question: str
    # The grouping it is split by, if any.
    by: str | None
    # Each bar's series, with how many releases' researchers answered.
    series: list[tuple[str, int]]
    bars: list[Bar]


@dataclass(frozen=True)
class Standing:
    entry: Entry
    # The analysed releases' median on this key.
    median: float | None
    # How far above (+) or below (−) that median, in per cent; None when the median is 0.
    difference: float | None


# The All releases page: the score and the three numbers that travel (Daniel, 2026-11-12).
RELEASE_TABLE_KEYS = (SCORE, "hp_views.d28", "ea_views.d28", ALTMETRIC)


def _ranked_order(entry: Entry) -> tuple:
    """Highest first; equal values by the unrounded score, then the newer release; no value
    last, newest first."""
    has_value = entry.value is not None
    return (
        not has_value,
        -(entry.value or 0.0),
        -(entry.exact or 0.0),
        -entry.row.release_date.toordinal(),
        entry.row.code or "",
    )


def basis_or_default(asked: str | None, spec: ProfileSpec | None) -> str:
    if asked in (BASIS_INCREASE, BASIS_DAY28):
        return asked
    return spec.altmetric_basis if spec else BASIS_INCREASE
