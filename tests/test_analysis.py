"""The analysis read layer and the score (phase-2 brief §4). The expected numbers are worked
out by hand below, so the formula is pinned, not just re-run."""

import uuid
from datetime import date, timedelta

import pytest

from app.services.analysis.dataset import MISSING, NOT_APPLICABLE, Cell, Dataset, Row
from app.services.analysis.filters import AnalysisFilter
from app.services.analysis.scoring import ProfileSpec, score_releases, top
from app.services.analysis.stats import mid_rank, quantile_inc, whole

TODAY = date(2026, 3, 31)
PAPER = uuid.uuid4()
FEATURE = uuid.uuid4()
ANALYSED = AnalysisFilter(release_types=frozenset({PAPER}))


def _row(name: str, cells: dict, *, finished=True, year=2025, kind=PAPER) -> Row:
    released = TODAY - timedelta(days=40 if finished else 10)
    return Row(
        id=uuid.uuid5(uuid.NAMESPACE_URL, name),
        code=name,
        title=name,
        release_date=released,
        academic_year=year,
        release_type_id=kind,
        unit_id=None,
        field_id=None,
        embargoed=False,
        gender="not_recorded",
        finished=finished,
        cells={
            key: value if isinstance(value, Cell) else Cell("value", float(value))
            for key, value in cells.items()
        },
    )


NA, MS = NOT_APPLICABLE, MISSING
ROWS = [
    _row("r1", {"A": 10, "B": 5, "C": NA}),
    _row("r2", {"A": 20, "B": 5, "C": 1}),
    _row("r3", {"A": 20, "B": MS, "C": 2}),
    _row("r4", {"A": 30, "B": 7, "C": 3}),
    _row("r5", {"A": 40, "B": NA, "C": NA}),
    _row("r6", {"A": MS, "B": MS, "C": 4}),
    _row("r7", {"A": 25, "B": 9, "C": MS}, finished=False),
    _row("r8", {"A": 100, "B": 100, "C": 100}, kind=FEATURE),
]
SPEC = ProfileSpec(weights={"A": 50, "B": 30, "C": 20}, min_values=1)


def _scores(spec=SPEC, rows=ROWS, analysed=ANALYSED):
    found = score_releases(Dataset(TODAY, [], rows), spec, analysed)
    return {row.code: found.get(row.id) for row in rows}


def test_the_score_formula_worked_out_by_hand():
    """S = r1–r6 (finished, peer-reviewed). Values in S: A [10, 20, 20, 30, 40],
    B [5, 5, 7], C [1, 2, 3, 4].

    r1: A (0 + ½)/5 = 10; B (0 + 2/2)/3 = 33.33; C n/a → base 80, all covered,
        (500 + 1000)/80 = 18.75
    r2: A (1 + 2/2)/5 = 40; B 33.33; C (0 + ½)/4 = 12.5 → (2000 + 1000 + 250)/100 = 32.5
    r3: A 40; B missing; C (1 + ½)/4 = 37.5 → covered 70 of 100 = 70 %, (2000 + 750)/70 = 39.29
    r4: A (3 + ½)/5 = 70; B (2 + ½)/3 = 83.33; C (2 + ½)/4 = 62.5 → (3500 + 2500 + 1250)/100 = 72.5
    r5: A (4 + ½)/5 = 90; B and C n/a → base 50, 100 %, 90
    r6: only C (3 + ½)/4 = 87.5 → covered 20 of 100 = 20 % < 60 %: insufficient data
    r7 (provisional, ranked as if in S): A (3 + ½)/6 = 58.33; B (3 + ½)/4 = 87.5; C missing
        → covered 80 of 100, (2916.67 + 2625)/80 = 69.27
    r8: a feature, outside the analysed set: no score at all
    """
    scores = _scores()
    expected = {"r1": 19, "r2": 33, "r3": 39, "r4": 73, "r5": 90, "r6": None, "r7": 69}
    assert {code: score.value for code, score in scores.items() if score} == expected
    assert scores["r8"] is None

    assert scores["r1"].exact == pytest.approx(18.75)
    assert scores["r2"].exact == pytest.approx(32.5)
    assert scores["r3"].exact == pytest.approx(2750 / 70)
    assert scores["r3"].coverage == pytest.approx(0.7)
    assert scores["r3"].components == ["A", "C"]
    assert scores["r4"].percentiles == pytest.approx({"A": 70, "B": 250 / 3, "C": 62.5})
    assert scores["r6"].insufficient and scores["r6"].coverage == pytest.approx(0.2)
    assert scores["r7"].provisional and not scores["r4"].provisional
    assert scores["r7"].exact == pytest.approx((50 * 350 / 6 + 30 * 87.5) / 80)
    # Half up, as in Excel: 32.5 → 33, 72.5 → 73.
    assert (scores["r2"].value, scores["r4"].value) == (33, 73)


def test_a_component_with_too_few_values_counts_as_missing():
    """Minimum values 5: A has 5, B 3 and C 4 in S, so only A counts. r1: A alone covers 50 of 80
    = 62.5 %, enough; r2: 50 of 100, not enough. r7 brings its own value: B has 4, still short."""
    scores = _scores(ProfileSpec(weights={"A": 50, "B": 30, "C": 20}, min_values=5))
    assert scores["r1"].value == 10 and scores["r1"].components == ["A"]
    assert scores["r2"].insufficient
    assert scores["r5"].value == 90


def test_the_coverage_minimum_is_a_profile_setting():
    scores = _scores(
        ProfileSpec(weights={"A": 50, "B": 30, "C": 20}, min_values=1, coverage_min=10)
    )
    assert scores["r6"].value == 88  # 87.5, half up


def test_the_comparison_set_is_the_releases_year_and_the_two_before():
    old = _row("old", {"A": 1000, "B": NA, "C": NA}, year=2022)
    three_years = _row("y2023", {"A": 0, "B": NA, "C": NA}, year=2023)
    scores = _scores(rows=[*ROWS, old, three_years])
    # AY2023 is within AY2025's window (2023–2025); AY2022 is not. r5 (40) is now 5 of 6 below.
    assert scores["r5"].percentiles["A"] == pytest.approx((5 + 0.5) / 6 * 100)
    # The AY2022 release is ranked against AY2020–2022 only: itself.
    assert scores["old"].percentiles["A"] == pytest.approx(50)


def test_narrowing_the_analysed_set_narrows_the_comparison_set():
    everything = _scores(analysed=AnalysisFilter())
    # The feature joins S: A [10, 20, 20, 30, 40, 100].
    assert everything["r8"].value is not None
    assert everything["r5"].percentiles["A"] == pytest.approx((4 + 0.5) / 6 * 100)


def test_top_and_bottom_leave_provisional_and_insufficient_releases_out():
    dataset = Dataset(TODAY, [], ROWS)
    scores = score_releases(dataset, SPEC, ANALYSED)
    assert [row.code for row, _ in top(dataset, scores, ANALYSED)] == ["r5", "r4", "r3", "r2", "r1"]
    assert [row.code for row, _ in top(dataset, scores, ANALYSED, lowest=True)][:2] == ["r1", "r2"]


def test_quartiles_follow_excel_quartile_inc():
    # =QUARTILE.INC({1,2,3,4}, 1) is 1.75, the median 2.5, the third quartile 3.25.
    values = [1, 2, 3, 4]
    assert [quantile_inc(values, q) for q in (0, 0.25, 0.5, 0.75, 1)] == [1, 1.75, 2.5, 3.25, 4]
    assert quantile_inc([7], 0.5) == 7
    assert quantile_inc([], 0.5) is None
    # =QUARTILE.INC({109, 150, 180, 247, 400}, 1) is 150.
    assert quantile_inc([109, 150, 180, 247, 400], 0.25) == 150


def test_mid_rank_and_rounding():
    assert mid_rank(5, [5, 5, 7], include_self=False) == (pytest.approx(100 / 3), 3)
    assert mid_rank(6, [5, 5, 7], include_self=True) == (pytest.approx(62.5), 4)
    assert [whole(x) for x in (0.5, 1.5, 2.5, 69.49)] == [1, 2, 3, 69]


# ---------------------------------------------------------------- from the database


async def test_the_dataset_reads_every_state_from_the_database():
    from datetime import UTC, datetime
    from decimal import Decimal

    from sqlalchemy import select

    from app.database import SessionLocal
    from app.models import Institution, Measure, Reading, Release, SurveyResponse
    from app.services.analysis import dataset as analysis
    from app.services.feedback.template import ensure_template
    from app.services.readings import today_in

    async with SessionLocal() as db:
        institution = await db.scalar(select(Institution))
        today = today_in(institution.timezone)
        made = {}
        for name, values in {
            "old": dict(
                release_date=today - timedelta(days=40),
                doi="10.1/a",
                publication_date=today - timedelta(days=40),
                ea_url="https://www.eurekalert.org/news-releases/1",
            ),
            "new": dict(
                release_date=today - timedelta(days=10),
                doi="10.1/b",
                publication_date=today - timedelta(days=60),
            ),
            "no_doi": dict(release_date=today - timedelta(days=50)),
            "removed": dict(release_date=today - timedelta(days=50), deleted_at=datetime.now(UTC)),
            "draft": dict(),
        }.items():
            release = Release(institution_id=institution.id, title=name, **values)
            db.add(release)
            made[name] = release
        await db.flush()
        day28 = await db.scalar(
            select(Reading)
            .join(Measure, Measure.id == Reading.measure_id)
            .where(Reading.release_id == made["old"].id, Measure.key == "altmetric.d28")
        )
        day28.value, day28.state, day28.source = Decimal(12), "value", "manual"
        template = await ensure_template(db, institution.id)
        db.add(
            SurveyResponse(
                institution_id=institution.id,
                template_id=template.id,
                release_id=made["old"].id,
                source="legacy_import",
                external_id="x1",
                answers={"sat_process": 5, "sat_accuracy": 4, "sat_understandability": 3},
            )
        )
        await db.commit()
        found = await analysis.load(db, institution, today)

    rows = {row.title: row for row in found.rows}
    assert set(rows) == {"old", "new", "no_doi"}
    old, new, no_doi = rows["old"], rows["new"], rows["no_doi"]
    assert old.finished and not new.finished
    # The paper came out on the release day: an inferred 0, and an increase marked inferred.
    assert old.cell("altmetric.d0") == Cell("value", 0.0, inferred=True)
    assert old.cell("altmetric_increase") == Cell("value", 12.0, inferred=True)
    assert old.cell("ea_views.d28").state == "missing"
    assert new.cell("ea_views.d28").state == "not_applicable"
    assert new.cell("altmetric.d28").state == "not_yet_due"
    assert new.cell("altmetric_increase").state == "not_yet_due"
    assert no_doi.cell("altmetric_increase").state == "not_applicable"
    # Pickups are not collected yet: not applicable to every release (R8.1.4).
    assert {row.cell("pickups_major").state for row in rows.values()} == {"not_applicable"}
    assert old.cell("satisfaction") == Cell("value", 4.0)
    assert new.cell("satisfaction").state == "missing"
    keys = [dimension.key for dimension in found.dimensions]
    assert {"altmetric_increase", "satisfaction", "inquiries_external", "pickups_all"} <= set(keys)
    increase = found.dimension("altmetric_increase")
    assert increase.label_ja.startswith("Altmetric") and increase.decimals == 2
