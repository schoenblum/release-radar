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


class OverviewOut(BaseModel):
    scope: ScopeOut
    cards: list[CardOut]


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


class DimensionOut(BaseModel):
    scope: ScopeOut
    card: CardOut
    rows: list[EntryOut]


class TopOut(BaseModel):
    scope: ScopeOut
    key: str
    label_en: str
    label_ja: str
    unit: str
    decimals: int
    highest: list[EntryOut]
    lowest: list[EntryOut]


class PositionsOut(BaseModel):
    """Percentiles per release and measure for the Data page (BRIEF §8.4). A release that is not
    a key is outside the default analysis."""

    measures: list[str]
    releases: dict[uuid.UUID, dict[str, float]]
