"""The Analysis pages' answers (phase-2 brief §5). Office only: every signed-in role (D16)."""

import uuid
from datetime import date

from pydantic import BaseModel


class OptionOut(BaseModel):
    # A list entry's ID, "none" for releases without one, a year, "1"/"0", or a gender.
    value: str
    label_en: str | None = None
    label_ja: str | None = None
    short_en: str | None = None
    count: int


class PageOut(BaseModel):
    key: str
    label_en: str
    label_ja: str


class ProfileRef(BaseModel):
    id: uuid.UUID
    version: int
    name_en: str
    name_ja: str | None
    is_default: bool
    altmetric_basis: str
    coverage_min: int
    comparison_years: int
    min_values: int


class FilterOut(BaseModel):
    """A filter as it applies, after the institution's defaults: None means every value."""

    type: list[str] | None = None
    ay: list[str] | None = None
    unit: list[str] | None = None
    field: list[str] | None = None
    emb: list[str] | None = None
    gender: list[str] | None = None


class DefaultsOut(BaseModel):
    """Where both filters start (R6.4.2): what an address without them means."""

    analysed: FilterOut
    shown: FilterOut


class OptionsOut(BaseModel):
    """What the two filters offer, every page, and every profile. Values with releases only."""

    defaults: DefaultsOut
    release_types: list[OptionOut]
    academic_years: list[OptionOut]
    units: list[OptionOut]
    fields: list[OptionOut]
    embargoed: list[OptionOut]
    genders: list[OptionOut]
    pages: list[PageOut]
    profiles: list[ProfileRef]
    # The survey questions with answers, each with a page of its own.
    answers: list[str] = []


class ScopeOut(BaseModel):
    analysed: FilterOut
    shown: FilterOut
    analysed_count: int
    shown_count: int
    first_year: int | None
    last_year: int | None
    profile: ProfileRef | None
    altmetric_basis: str
    today: date


class BoxOut(BaseModel):
    low: float
    q1: float
    median: float
    q3: float
    high: float
    n: int


class CountsOut(BaseModel):
    value: int
    missing: int
    not_applicable: int
    not_yet_due: int
    insufficient: int
    provisional: int


class PointOut(BaseModel):
    id: uuid.UUID
    code: str | None
    title: str | None
    release_date: date
    value: float
    inferred: bool


class CardOut(BaseModel):
    key: str
    dimension: str
    label_en: str
    label_ja: str
    unit: str
    decimals: int
    box: BoxOut | None
    counts: CountsOut
    points: list[PointOut]
    shown_median: float | None


class YearMedianOut(BaseModel):
    year: int
    median: float
    n: int
    first: date
    last: date


class ShareOut(BaseModel):
    # The bar's series: a group's value, or "shown" / "analysed".
    series: str
    count: int
    share: float


class BarOut(BaseModel):
    key: str
    label_en: str
    label_ja: str
    shares: list[ShareOut]


class AnswerSeriesOut(BaseModel):
    key: str
    respondents: int


class AnswerChartOut(BaseModel):
    """A survey question as bars: the share of respondents who ticked each box, for the shown
    releases (and the analysed ones to compare), or per group of a grouping."""

    question: str
    # The grouping (ay, type, field, unit, emb, gender), or None.
    by: str | None
    series: list[AnswerSeriesOut]
    bars: list[BarOut]


class AnswerChoiceOut(BaseModel):
    key: str
    label_en: str
    label_ja: str


class AnswerRowOut(BaseModel):
    """A shown release on a survey question's page: the boxes its researchers ticked."""

    id: uuid.UUID
    code: str | None
    title: str | None
    release_date: date
    academic_year: int
    unit_id: uuid.UUID | None
    field_id: uuid.UUID | None
    answered: bool
    ticked: list[str]


class AnswersOut(BaseModel):
    """A survey question's own page (Daniel, 2026-11-13): its bars, split by ``group_by`` if
    asked, and every shown release with what its researchers ticked."""

    scope: ScopeOut
    question: str
    group_by: str | None
    chart: AnswerChartOut | None
    choices: list[AnswerChoiceOut]
    rows: list[AnswerRowOut]


class OverviewOut(BaseModel):
    scope: ScopeOut
    cards: list[CardOut]
    # The score's median per academic year, for the score over time.
    score_years: list[YearMedianOut]
    # Inquiries and activities from researcher feedback (Daniel, 2026-11-12).
    answers: list[AnswerChartOut]


class EntryOut(BaseModel):
    id: uuid.UUID
    code: str | None
    title: str | None
    release_date: date
    academic_year: int
    unit_id: uuid.UUID | None
    field_id: uuid.UUID | None
    value: float | None
    state: str
    inferred: bool
    provisional: bool
    rank: int | None
    percentile: float | None
    coverage: float | None
    components: list[str]


class GroupOut(BaseModel):
    """One group of a split chart; its value as the address writes it (an ID, a year, "none",
    "1"/"0", a gender)."""

    value: str
    n: int
    median: float
    # None below five values: dots and median only.
    box: BoxOut | None
    points: list[PointOut]
    shown_median: float | None


class DimensionOut(BaseModel):
    scope: ScopeOut
    card: CardOut
    rows: list[EntryOut]
    # The grouping asked for and its groups (Daniel, 2026-11-12); None when not split.
    group_by: str | None = None
    groups: list[GroupOut] | None = None


class TopOut(BaseModel):
    scope: ScopeOut
    key: str
    label_en: str
    label_ja: str
    unit: str
    decimals: int
    highest: list[EntryOut]
    lowest: list[EntryOut]


class StandingOut(BaseModel):
    value: float | None
    state: str
    provisional: bool
    # How far above (+) or below (−) the analysed median, in per cent.
    difference: float | None


class ReleaseLineOut(BaseModel):
    id: uuid.UUID
    code: str | None
    title: str | None
    release_date: date
    standings: dict[str, StandingOut]


class ReleaseColumnOut(BaseModel):
    key: str
    label_en: str
    label_ja: str
    unit: str
    decimals: int
    median: float | None


class ReleasesOut(BaseModel):
    """Analysis → All releases: each shown release on the score and three numbers."""

    scope: ScopeOut
    columns: list[ReleaseColumnOut]
    releases: list[ReleaseLineOut]
