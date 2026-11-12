"""Every release with every dimension's value and state (phase-2 brief §4.1).

Dimensions are every measure, plus what is derived from them and from researcher feedback:
the Altmetric increase (d28 − d0), satisfaction, research outcomes, inquiries and inquiries from
outside. Measures added later (the journal metric, pickups in Phase 4) appear here without any
change to the pages. Scores are dimensions too, added by ``scoring``.

States are the four of R6.5.1: *value*, *not_applicable*, *missing* (stored), and *not_yet_due*
(computed from the checkpoint's date). A value may be *inferred* (R8.1.3).
"""

import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.i18n import t
from app.models import Checkpoint, Institution, Measure, Reading, Release, Researcher
from app.models.survey import SurveyItem
from app.services.feedback import dimensions as feedback
from app.services.feedback.template import ACTIVITIES, INQUIRIES
from app.services.readings import (
    STATE_MISSING,
    STATE_NOT_APPLICABLE,
    STATE_NOT_YET_DUE,
    STATE_VALUE,
    display_state,
    due_date,
)
from app.services.release_codes import academic_year

# A release is finished when day 28 has passed and the website-views fetch has had its chance
# (the 2 days Google Analytics needs to process a day). Before that its score is provisional.
FINISHED_AFTER_DAYS = 30
ALTMETRIC_INCREASE = "altmetric_increase"
FEEDBACK_DIMENSIONS = ("satisfaction", "research_outcomes", "inquiries", "inquiries_external")
# Units whose numbers keep decimals; everything else is a whole number.
_DECIMAL_UNITS = frozenset({"score", "scale"})


@dataclass(frozen=True)
class Dimension:
    key: str
    label_en: str
    label_ja: str
    unit: str
    decimals: int
    # measure, derived or score.
    kind: str
    # Higher is better, for every dimension so far.
    higher_is_better: bool = True


@dataclass(frozen=True)
class Cell:
    state: str
    value: float | None = None
    inferred: bool = False

    @property
    def has_value(self) -> bool:
        return self.state == STATE_VALUE and self.value is not None


NOT_APPLICABLE = Cell(STATE_NOT_APPLICABLE)
MISSING = Cell(STATE_MISSING)
NOT_YET_DUE = Cell(STATE_NOT_YET_DUE)


@dataclass
class Row:
    id: uuid.UUID
    code: str | None
    title: str | None
    release_date: date
    academic_year: int
    release_type_id: uuid.UUID | None
    unit_id: uuid.UUID | None
    field_id: uuid.UUID | None
    embargoed: bool
    gender: str
    finished: bool
    cells: dict[str, Cell] = field(default_factory=dict)
    # Per survey question (inquiries, activities): the boxes ticked; None if not answered.
    answers: dict[str, frozenset[str] | None] = field(default_factory=dict)

    def cell(self, key: str) -> Cell:
        # A dimension a release has no reading for cannot exist for it.
        return self.cells.get(key, NOT_APPLICABLE)


@dataclass(frozen=True)
class Choice:
    """One box of a survey question, as the Overview's bar charts name it."""

    question: str
    key: str
    label_en: str
    label_ja: str


@dataclass
class Dataset:
    today: date
    dimensions: list[Dimension]
    rows: list[Row]
    choices: list[Choice] = field(default_factory=list)

    def dimension(self, key: str) -> Dimension | None:
        return next((item for item in self.dimensions if item.key == key), None)


def _derived_applies(measure: Measure, release_date: date) -> bool:
    """A calculated count (pickups) exists only from the date the institution collects it
    (R6.7.1, R10.10). Without that date it is not applicable to anything: otherwise the default
    profile would count 45 % of its weight as missing and score nothing (R8.1.4)."""
    return (
        measure.is_active
        and measure.collected_from is not None
        and release_date >= measure.collected_from
    )


def _increase(day0: Cell, day28: Cell) -> Cell:
    """d28 − d0 (D15): N/A if either is, not yet due until day 28 is, missing if either is."""
    if STATE_NOT_APPLICABLE in (day0.state, day28.state):
        return NOT_APPLICABLE
    if day28.state == STATE_NOT_YET_DUE:
        return NOT_YET_DUE
    if not (day0.has_value and day28.has_value):
        return MISSING
    return Cell(STATE_VALUE, day28.value - day0.value, inferred=day0.inferred)


def _labelled(key: str, unit: str, decimals: int, kind: str) -> Dimension:
    return Dimension(
        key=key,
        label_en=t("en", f"analysis.dimensions.{key}"),
        label_ja=t("ja", f"analysis.dimensions.{key}"),
        unit=unit,
        decimals=decimals,
        kind=kind,
    )


def dimensions_of(measures: list[Measure]) -> list[Dimension]:
    """Every dimension there is, in order: the measures, then what is derived from them."""
    dimensions = [
        Dimension(
            key=measure.key,
            label_en=measure.label_en,
            label_ja=measure.label_ja or measure.label_en,
            unit=measure.unit,
            decimals=2 if measure.unit in _DECIMAL_UNITS else 0,
            kind="measure",
        )
        for measure in measures
        if measure.is_active or measure.source == "derived"
    ]
    keys = {measure.key for measure in measures}
    if {"altmetric.d0", "altmetric.d28"} <= keys:
        dimensions.append(_labelled(ALTMETRIC_INCREASE, "score", 2, "derived"))
    dimensions += [
        _labelled("satisfaction", "scale", 2, "derived"),
        _labelled("research_outcomes", "count", 0, "derived"),
        _labelled("inquiries", "count", 0, "derived"),
        _labelled("inquiries_external", "count", 0, "derived"),
    ]
    return dimensions


async def measures_of(db: AsyncSession, institution_id: uuid.UUID) -> list[Measure]:
    return list(
        await db.scalars(
            select(Measure)
            .where(Measure.institution_id == institution_id)
            .order_by(Measure.position, Measure.key)
        )
    )


async def choices_of(db: AsyncSession, institution_id: uuid.UUID) -> list[Choice]:
    """The boxes of the inquiries and activities questions, in the survey's order. Keys are
    stable across template versions (R11.1); the newest template's wording wins."""
    found: dict[str, Choice] = {}
    order: dict[str, int] = {}
    items = await db.scalars(
        select(SurveyItem)
        .where(
            SurveyItem.institution_id == institution_id,
            SurveyItem.question.in_((INQUIRIES, ACTIVITIES)),
            SurveyItem.exclusive.is_(False),
        )
        .order_by(SurveyItem.created_at)
    )
    for item in items:
        found[item.key] = Choice(
            item.question, item.key, item.label_en, item.label_ja or item.label_en
        )
        order.setdefault(item.key, item.position)
    return sorted(found.values(), key=lambda choice: order[choice.key])


async def load(db: AsyncSession, institution: Institution, today: date) -> Dataset:
    """Every dated release that has not been removed, with all its dimensions."""
    measures = await measures_of(db, institution.id)
    offsets = {
        checkpoint.id: checkpoint.offset_days
        for checkpoint in await db.scalars(
            select(Checkpoint).where(Checkpoint.institution_id == institution.id)
        )
    }
    releases = list(
        await db.scalars(
            select(Release)
            .where(
                Release.institution_id == institution.id,
                Release.deleted_at.is_(None),
                Release.release_date.is_not(None),
            )
            .order_by(Release.release_date, Release.code)
        )
    )
    readings: dict[tuple[uuid.UUID, uuid.UUID], Reading] = {
        (reading.release_id, reading.measure_id): reading
        for reading in await db.scalars(
            select(Reading).where(Reading.institution_id == institution.id)
        )
    }
    genders = dict(
        (
            await db.execute(
                select(Researcher.id, Researcher.gender).where(
                    Researcher.institution_id == institution.id
                )
            )
        ).all()
    )
    responses = await feedback.by_release(db, institution.id)

    dimensions = dimensions_of(measures)

    rows: list[Row] = []
    for release in releases:
        row = Row(
            id=release.id,
            code=release.code,
            title=release.title,
            release_date=release.release_date,
            academic_year=academic_year(release.release_date, institution.ay_start_month),
            release_type_id=release.release_type_id,
            unit_id=release.unit_id,
            field_id=release.field_id,
            embargoed=release.embargoed,
            gender=genders.get(release.researcher_id, "not_recorded") or "not_recorded",
            finished=release.release_date + timedelta(days=FINISHED_AFTER_DAYS) <= today,
        )
        for measure in measures:
            if measure.source == "derived":
                if not _derived_applies(measure, release.release_date):
                    row.cells[measure.key] = NOT_APPLICABLE
                    continue
            elif not measure.is_active:
                continue
            reading = readings.get((release.id, measure.id))
            if reading is None:
                # A calculated count is a value from its date on: 0 if nothing was counted, never
                # missing (R6.7.1). Any other measure without a reading cannot exist here.
                row.cells[measure.key] = (
                    Cell(STATE_VALUE, 0.0) if measure.source == "derived" else NOT_APPLICABLE
                )
                continue
            if reading.state == STATE_VALUE:
                row.cells[measure.key] = Cell(
                    STATE_VALUE, float(reading.value), inferred=reading.inferred
                )
                continue
            due = due_date(release.release_date, offsets.get(measure.checkpoint_id))
            state = display_state(reading.state, due, today)
            row.cells[measure.key] = Cell(state)
        if ALTMETRIC_INCREASE in {d.key for d in dimensions}:
            row.cells[ALTMETRIC_INCREASE] = _increase(
                row.cell("altmetric.d0"), row.cell("altmetric.d28")
            )
        found = responses.get(release.id)
        for key in FEEDBACK_DIMENSIONS:
            value = getattr(found, key) if found is not None else None
            row.cells[key] = MISSING if value is None else Cell(STATE_VALUE, float(value))
        row.answers = {
            INQUIRIES: found.inquiry_keys if found else None,
            ACTIVITIES: found.activity_keys if found else None,
        }
        rows.append(row)
    return Dataset(
        today=today,
        dimensions=dimensions,
        rows=rows,
        choices=await choices_of(db, institution.id),
    )
