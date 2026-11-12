"""The Analysis pages (phase-2 brief §5): cards, rankings, top and bottom, all releases, the
survey's bar charts, the two filters in the address, exports and who may read them. Synthetic
data; expected numbers worked out by hand."""

import csv
import io
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from openpyxl import load_workbook
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Institution, Measure, Reading, Release, ReleaseType, Unit, UserRole
from app.services.analysis.dataset import (
    MISSING,
    NOT_APPLICABLE,
    Cell,
    Choice,
    Dataset,
    Dimension,
    Row,
)
from app.services.analysis.filters import AnalysisFilter
from app.services.analysis.pages import Analysis, page_keys
from app.services.analysis.scoring import ProfileSpec
from app.services.readings import today_in
from tests.conftest import bearer, sign_in

TODAY = date(2026, 3, 31)
PAPER = uuid.uuid4()
FEATURE = uuid.uuid4()
SCIENCE = uuid.uuid4()
ANALYSED = AnalysisFilter(release_types=frozenset({PAPER}))
VIEWS = Dimension("views", "Views", "閲覧数", "views", 0, "measure")


def _row(name, value, *, finished=True, kind=PAPER, unit=None, year=2025) -> Row:
    cell = value if isinstance(value, Cell) else Cell("value", float(value))
    return Row(
        id=uuid.uuid5(uuid.NAMESPACE_URL, name),
        code=name,
        title=name,
        release_date=TODAY - timedelta(days=40 if finished else 10),
        academic_year=year,
        release_type_id=kind,
        unit_id=unit,
        field_id=None,
        embargoed=False,
        gender="not_recorded",
        finished=finished,
        cells={"views": cell},
    )


ROWS = [
    _row("r1", 109, unit=SCIENCE),
    _row("r2", 150),
    _row("r3", 180, unit=SCIENCE),
    _row("r4", 180),
    _row("r5", 247, unit=SCIENCE),
    _row("r6", 400),
    _row("r7", MISSING),
    _row("r8", NOT_APPLICABLE),
    _row("r9", 500, finished=False),
    _row("feature", 9999, kind=FEATURE),
]
SPEC = ProfileSpec(weights={"views": 100}, min_values=1)


def _analysis(rows=ROWS, shown=AnalysisFilter(), spec=SPEC, analysed=ANALYSED) -> Analysis:
    return Analysis(Dataset(TODAY, [VIEWS], rows), analysed, shown, spec, "increase")


def test_the_box_describes_the_analysed_releases_and_the_points_are_the_shown():
    """Analysed with a value: 109, 150, 180, 180, 247, 400, 500 (r9 is provisional, but a value
    is a value; only a score waits for day 30). QUARTILE.INC: Q1 = 165, median 180, Q3 = 323.5.
    The feature is outside the analysed set and counts nowhere."""
    card = _analysis(shown=AnalysisFilter(units=frozenset({SCIENCE}))).card("views")
    assert (card.box.low, card.box.q1, card.box.median, card.box.q3, card.box.high) == (
        109,
        165,
        180,
        323.5,
        500,
    )
    assert card.box.n == 7
    assert (card.counts.value, card.counts.missing, card.counts.not_applicable) == (7, 1, 1)
    # Shown: the three Science releases, median 180.
    assert [point.row.code for point in card.points] == ["r1", "r3", "r5"]
    assert card.shown_median == 180


def test_narrowing_the_shown_set_never_changes_a_number_computed_from_the_analysed():
    everything = _analysis().card("views")
    narrowed = _analysis(shown=AnalysisFilter(units=frozenset({SCIENCE}))).card("views")
    assert everything.box == narrowed.box
    assert vars(everything.counts) == vars(narrowed.counts)
    ranks = {entry.row.code: entry.rank for entry in _analysis().rows("views")}
    narrow_ranks = {
        entry.row.code: entry.rank
        for entry in _analysis(shown=AnalysisFilter(units=frozenset({SCIENCE}))).rows("views")
    }
    assert {code: ranks[code] for code in narrow_ranks} == narrow_ranks


def test_ranks_share_ties_and_rows_without_a_value_come_last():
    rows = _analysis().rows("views")
    assert [(entry.row.code, entry.rank) for entry in rows] == [
        ("r9", 1),
        ("r6", 2),
        ("r5", 3),
        # 180 twice: both 4th, and the next is 6th.
        ("r3", 4),
        ("r4", 4),
        ("r2", 6),
        ("r1", 7),
        ("r7", None),
        ("r8", None),
    ]
    assert rows[0].provisional and not rows[1].provisional
    assert {entry.row.code: entry.state for entry in rows}["r8"] == "not_applicable"


def test_the_percentile_is_the_one_the_score_uses():
    """Comparison set: the finished analysed releases, 109 150 180 180 247 400 (n = 6).
    r3 (180): (2 below + 2/2) / 6 = 50. r9 is provisional, ranked as if in the set:
    (6 below + ½) / 7 = 92.86."""
    found = {entry.row.code: entry.percentile for entry in _analysis().rows("views")}
    assert found["r3"] == pytest.approx(50)
    assert found["r9"] == pytest.approx(650 / 7)
    assert found["r7"] is None
    # Below the profile's minimum of values, there is no percentile, as there is no score part.
    few = _analysis(spec=ProfileSpec(weights={"views": 100}, min_values=7))
    assert {entry.row.code: entry.percentile for entry in few.rows("views")}["r3"] is None
    # r9 brings its own value: 7 in all, enough.
    assert {entry.row.code: entry.percentile for entry in few.rows("views")}["r9"] is not None


def test_the_score_page_ranks_final_scores_and_gives_a_provisional_one_its_place():
    found = _analysis()
    scores = {entry.row.code: entry for entry in found.rows("score")}
    # Score = the percentile (one component). r6: (5 + ½) / 6 = 91.67 → 92, rank 1.
    assert (scores["r6"].value, scores["r6"].rank) == (92, 1)
    # r9 would score 93 (92.86): above everyone, so rank 1, and provisional.
    assert (scores["r9"].value, scores["r9"].rank, scores["r9"].provisional) == (93, 1, True)
    assert scores["r7"].state == "insufficient" and scores["r7"].rank is None
    card = found.card("score")
    # r7 has no value and r8 none that applies: neither gets a score.
    assert card.counts.provisional == 1 and card.counts.insufficient == 2
    # The box is over final scores only: six of them.
    assert card.box.n == 6 and all(not point.provisional for point in card.points)


def test_top_and_bottom_keep_provisional_and_insufficient_releases_out():
    highest, lowest = _analysis().top_and_bottom("score")
    assert [entry.row.code for entry in highest] == ["r6", "r5", "r3", "r4", "r2"]
    # Six finished with a score: the lowest list takes what the highest left, never r9 or r7.
    assert [entry.row.code for entry in lowest] == ["r1"]
    highest, lowest = _analysis().top_and_bottom("views", count=3)
    assert [entry.row.code for entry in highest] == ["r6", "r5", "r3"]
    assert [entry.row.code for entry in lowest] == ["r1", "r2", "r4"]


def test_pages_exist_for_dimensions_with_data_with_altmetric_once():
    dimensions = [
        Dimension(key, key, key, "views", 0, "measure")
        for key in ("altmetric.d0", "altmetric.d28", "ea_views.d28", "pickups_all")
    ] + [Dimension("altmetric_increase", "i", "i", "score", 2, "derived")]
    row = _row("one", 1)
    row.cells = {
        "altmetric.d28": Cell("value", 3.0),
        "altmetric.d0": Cell("value", 1.0),
        "altmetric_increase": Cell("value", 2.0),
        "ea_views.d28": Cell("value", 10.0),
        "pickups_all": NOT_APPLICABLE,
    }
    assert page_keys(Dataset(TODAY, dimensions, [row])) == ["score", "altmetric", "ea_views.d28"]


# ---------------------------------------------------------------- through the API

URL = "/api/v1/analysis"


async def _releases(specs: list[dict]) -> dict[str, Release]:
    """Releases with day-28 EurekAlert views; type, unit, age and embargo as given."""
    made: dict[str, Release] = {}
    async with SessionLocal() as db:
        institution = await db.scalar(select(Institution))
        today = today_in(institution.timezone)
        types = dict((await db.execute(select(ReleaseType.key, ReleaseType.id))).all())
        for spec in specs:
            unit_id = None
            if spec.get("unit"):
                unit = await db.scalar(select(Unit).where(Unit.key == spec["unit"]))
                if unit is None:
                    unit = Unit(
                        institution_id=institution.id, key=spec["unit"], name_en=spec["unit"]
                    )
                    db.add(unit)
                    await db.flush()
                unit_id = unit.id
            release = Release(
                institution_id=institution.id,
                title=f"Release {spec['code']}",
                code=spec["code"],
                release_date=today - timedelta(days=spec.get("days", 40)),
                ea_url=f"https://www.eurekalert.org/news-releases/{len(made) + 1000}",
                release_type_id=types[spec.get("type", "peer_reviewed")],
                unit_id=unit_id,
                embargoed=spec.get("embargoed", False),
            )
            db.add(release)
            await db.flush()
            if "views" in spec:
                reading = await db.scalar(
                    select(Reading)
                    .join(Measure, Measure.id == Reading.measure_id)
                    .where(Reading.release_id == release.id, Measure.key == "ea_views.d28")
                )
                reading.value, reading.state, reading.source = (
                    Decimal(spec["views"]),
                    "value",
                    "manual",
                )
            made[spec["code"]] = release
        await db.commit()
    return made


SPECS = [
    {"code": "AY2026-01", "views": 100, "unit": "sci"},
    {"code": "AY2026-02", "views": 200},
    {"code": "AY2026-03", "views": 300, "unit": "sci"},
    {"code": "AY2026-04", "views": 400},
    {"code": "AY2026-05", "views": 900, "type": "feature"},
    {"code": "AY2026-06", "views": 50, "days": 5},
]


async def test_the_overview_follows_both_filters_in_the_address(client, headers_for):
    made = await _releases(SPECS)
    viewer = await headers_for(UserRole.viewer)
    response = await client.get(f"{URL}/overview", headers=viewer)
    assert response.status_code == 200, response.text
    body = response.json()
    scope = body["scope"]
    # The institution's defaults: peer-reviewed for both.
    assert scope["analysed_count"] == 5 and scope["shown_count"] == 5
    assert scope["profile"]["name_en"] == "News performance"
    assert (
        scope["analysed"]["type"] == scope["shown"]["type"] and len(scope["analysed"]["type"]) == 1
    )
    cards = {card["key"]: card for card in body["cards"]}
    assert list(cards)[0] == "score"
    views = cards["ea_views.d28"]
    # Analysed values 50, 100, 200, 300, 400 (the 5-day-old one has its day 28 typed already).
    assert views["box"]["median"] == 200 and views["box"]["n"] == 5
    assert views["shown_median"] == 200

    # Every type analysed; shown narrowed to one unit.
    unit = str(made["AY2026-01"].unit_id)
    body = (await client.get(f"{URL}/overview?a_type=all&s_unit={unit}", headers=viewer)).json()
    assert body["scope"]["analysed_count"] == 6 and body["scope"]["shown_count"] == 2
    views = {card["key"]: card for card in body["cards"]}["ea_views.d28"]
    assert views["box"]["median"] == 250  # 50 100 200 300 400 900
    assert sorted(point["value"] for point in views["points"]) == [100, 300]
    assert views["shown_median"] == 200
    assert body["scope"]["analysed"]["type"] is None


async def test_shown_stays_within_analysed_and_bad_values_fall_back(client, admin_headers):
    made = await _releases(SPECS)
    unit = str(made["AY2026-01"].unit_id)
    async with SessionLocal() as db:
        feature = await db.scalar(select(ReleaseType.id).where(ReleaseType.key == "feature"))
    # Shown asks for a type analysed leaves out: everything analysed is shown instead.
    body = (await client.get(f"{URL}/overview?s_type={feature}", headers=admin_headers)).json()
    assert body["scope"]["shown_count"] == body["scope"]["analysed_count"] == 5
    # Something that cannot be read is ignored, so an old bookmark still opens.
    body = (
        await client.get(
            f"{URL}/overview?a_unit=nonsense&a_ay=12&a_emb=maybe", headers=admin_headers
        )
    ).json()
    assert body["scope"]["analysed_count"] == 5
    # "none" stands for releases without a unit.
    body = (await client.get(f"{URL}/overview?a_unit=none", headers=admin_headers)).json()
    assert body["scope"]["analysed_count"] == 3
    body = (await client.get(f"{URL}/overview?a_unit={unit},none", headers=admin_headers)).json()
    assert body["scope"]["analysed_count"] == 5
    assert body["scope"]["analysed"]["unit"] == sorted([unit, "none"])


async def test_a_dimension_page_ranks_the_shown_releases(client, headers_for):
    await _releases(SPECS)
    viewer = await headers_for(UserRole.viewer)
    response = await client.get(f"{URL}/dimensions/ea_views.d28", headers=viewer)
    assert response.status_code == 200, response.text
    rows = response.json()["rows"]
    assert [(row["code"], row["rank"]) for row in rows] == [
        ("AY2026-04", 1),
        ("AY2026-03", 2),
        ("AY2026-02", 3),
        ("AY2026-01", 4),
        ("AY2026-06", 5),
    ]
    provisional = {row["code"]: row["provisional"] for row in rows}
    assert provisional["AY2026-06"] and not provisional["AY2026-04"]
    # The seeded profile wants 10 values per component; four finished are too few.
    assert {row["percentile"] for row in rows} == {None}
    assert (await client.get(f"{URL}/dimensions/nonsense", headers=viewer)).status_code == 404


async def test_top_and_bottom_by_a_dimension(client, headers_for):
    await _releases(SPECS)
    viewer = await headers_for(UserRole.viewer)
    body = (await client.get(f"{URL}/top?dimension=ea_views.d28", headers=viewer)).json()
    # Finished only: the 5-day-old release is in neither list.
    assert [row["code"] for row in body["highest"]] == [
        "AY2026-04",
        "AY2026-03",
        "AY2026-02",
        "AY2026-01",
    ]
    assert body["lowest"] == []
    assert body["label_en"].startswith("EurekAlert")


async def test_the_export_names_both_filters_the_profile_and_the_date(client, admin_headers):
    made = await _releases(SPECS)
    unit = str(made["AY2026-01"].unit_id)
    response = await client.get(
        f"{URL}/dimensions/ea_views.d28/export?s_unit={unit}&format=xlsx&language=en",
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    assert "release_radar_analysis_ea_views_d28_" in response.headers["content-disposition"]
    book = load_workbook(io.BytesIO(response.content))
    sheet = book.worksheets[0]
    rows = list(sheet.iter_rows(values_only=True))
    assert rows[0][:3] == ("Rank", "Code", "Title")
    assert [(row[0], row[1]) for row in rows[1:]] == [(2, "AY2026-03"), (4, "AY2026-01")]
    readme = "\n".join(str(cell.value) for cell in book["Read me"]["A"] if cell.value)
    assert "Analysed: 5 releases (Release type: Peer-reviewed publication)" in readme
    assert "Shown: 2 of them (Release type: Peer-reviewed publication; Unit: sci)" in readme
    assert "News performance, version 1" in readme
    assert "Exported on" in readme

    japanese = await client.get(
        f"{URL}/top/export?dimension=ea_views.d28&format=csv&language=ja", headers=admin_headers
    )
    assert japanese.status_code == 200
    text = japanese.content.decode("utf-8-sig")
    header = next(csv.reader(io.StringIO(text)))
    assert header[:3] == ["リスト", "順位", "コード"]
    assert "上位5件" in text


async def test_all_releases_stand_against_the_analysed_median(client, headers_for):
    """Daniel, 2026-11-12: the shown releases, newest first, on the score and three numbers,
    each as a per cent above or below the analysed releases' median."""
    made = await _releases(SPECS)
    viewer = await headers_for(UserRole.viewer)
    response = await client.get(f"{URL}/releases", headers=viewer)
    assert response.status_code == 200, response.text
    body = response.json()
    columns = {column["key"]: column for column in body["columns"]}
    # Only what has data: no website views or Altmetric in this synthetic set.
    assert list(columns) == ["score", "ea_views.d28"]
    assert columns["ea_views.d28"]["median"] == 200
    lines = {line["code"]: line for line in body["releases"]}
    # The feature is outside the analysed set; the newest comes first.
    assert "AY2026-05" not in lines
    assert body["releases"][0]["code"] == "AY2026-06"
    views = lines["AY2026-04"]["standings"]["ea_views.d28"]
    assert (views["value"], views["difference"]) == (400, 100)
    assert lines["AY2026-01"]["standings"]["ea_views.d28"]["difference"] == -50
    # Shown narrowed: fewer lines, the same median.
    unit = str(made["AY2026-01"].unit_id)
    body = (await client.get(f"{URL}/releases?s_unit={unit}", headers=viewer)).json()
    assert sorted(line["code"] for line in body["releases"]) == ["AY2026-01", "AY2026-03"]
    assert {c["key"]: c["median"] for c in body["columns"]}["ea_views.d28"] == 200


def test_the_score_has_a_median_per_academic_year():
    rows = [_row("a", 100, year=2024), _row("b", 300, year=2024), _row("c", 200, year=2025)]
    medians = _analysis(rows=rows).year_medians("views")
    assert [(item.year, item.median, item.n) for item in medians] == [
        (2024, 200, 2),
        (2025, 200, 1),
    ]


def _answered(name, year, inquiries, activities=None) -> Row:
    row = _row(name, 1, year=year)
    row.answers = {
        "inquiries": None if inquiries is None else frozenset(inquiries),
        "activities": None if activities is None else frozenset(activities),
    }
    return row


def test_the_survey_bars_count_only_releases_whose_researchers_answered():
    """Daniel, 2026-11-12: per cent of respondents who were contacted by each group, by year."""
    choices = [
        Choice("inquiries", "inq_media", "Media", "報道機関"),
        Choice("inquiries", "inq_public", "Public", "一般の方"),
        Choice("activities", "act_collab", "Joint research", "共同研究"),
    ]
    rows = [
        _answered("a", 2025, {"inq_media"}),
        _answered("b", 2025, {"inq_media", "inq_public"}),
        _answered("c", 2025, set()),  # answered "none"
        _answered("d", 2025, None),  # never answered: not a respondent
        _answered("e", 2026, {"inq_public"}, {"act_collab"}),
    ]
    found = Analysis(
        Dataset(TODAY, [VIEWS], rows, choices), ANALYSED, AnalysisFilter(), SPEC, "d28"
    )
    chart = found.answer_chart("inquiries")
    assert chart.years == [(2025, 3), (2026, 1)]
    media, public = chart.bars
    assert [(share.year, share.count) for share in media.shares] == [(2025, 2), (2026, 0)]
    assert media.shares[0].share == pytest.approx(200 / 3)
    assert [share.share for share in public.shares] == [pytest.approx(100 / 3), 100]
    activities = found.answer_chart("activities")
    assert activities.years == [(2026, 1)]
    # No question asked, or nobody answered: no chart.
    assert (
        Analysis(
            Dataset(TODAY, [VIEWS], rows[:1], []), ANALYSED, AnalysisFilter(), SPEC, "d28"
        ).answer_chart("inquiries")
        is None
    )


ENDPOINTS = [
    "/options",
    "/overview",
    "/dimensions/score",
    "/dimensions/score/export",
    "/top",
    "/top/export",
    "/releases",
]


@pytest.mark.parametrize("path", ENDPOINTS)
async def test_nothing_in_analysis_is_reachable_without_a_session(client, path):
    """Guest pages (survey, summary) come with tokens of their own later; none of them, nor a
    made-up token, reaches an Analysis endpoint."""
    assert (await client.get(f"{URL}{path}")).status_code == 401
    forged = await client.get(f"{URL}{path}", headers=bearer("survey-token-for-a-guest"))
    assert forged.status_code == 401


@pytest.mark.parametrize("role", [UserRole.viewer, UserRole.editor, UserRole.admin])
async def test_every_signed_in_role_reads_analysis(client, headers_for, role):
    await _releases(SPECS[:2])
    headers = await headers_for(role)
    for path in ENDPOINTS:
        response = await client.get(f"{URL}{path}", headers=headers)
        assert response.status_code == 200, (path, response.text)


async def test_the_options_list_what_the_filters_can_take(client, headers_for):
    await _releases(SPECS)
    body = (await client.get(f"{URL}/options", headers=await headers_for(UserRole.viewer))).json()
    types = {option["label_en"]: option["count"] for option in body["release_types"]}
    assert types == {"Peer-reviewed publication": 5, "Feature story": 1}
    assert {option["value"] for option in body["units"]} >= {"none"}
    assert [option["value"] for option in body["genders"]] == ["not_recorded"]
    assert [page["key"] for page in body["pages"]][:1] == ["score"]
    assert "ea_views.d28" in [page["key"] for page in body["pages"]]
    assert body["profiles"][0]["is_default"]
    async with SessionLocal() as db:
        peer = await db.scalar(select(ReleaseType.id).where(ReleaseType.key == "peer_reviewed"))
    assert body["defaults"]["analysed"] == {
        "type": [str(peer)],
        "ay": None,
        "unit": None,
        "field": None,
        "emb": None,
        "gender": None,
    }
    assert body["defaults"]["shown"]["type"] == [str(peer)]


async def test_another_profile_can_be_chosen(client, admin_headers):
    await _releases(SPECS)
    created = await client.post(
        "/api/v1/score-profiles",
        json={
            "name_en": "Views",
            "weights": {"ea_views.d28": 100},
            "min_values": 1,
        },
        headers=admin_headers,
    )
    profile = created.json()["id"]
    body = (await client.get(f"{URL}/top?profile={profile}", headers=admin_headers)).json()
    assert body["scope"]["profile"]["name_en"] == "Views"
    assert [row["code"] for row in body["highest"]][0] == "AY2026-04"
    unknown = await client.get(f"{URL}/overview?profile={uuid.uuid4()}", headers=admin_headers)
    assert unknown.status_code == 404


# ---------------------------------------------------------------- preferences and landing


async def test_preferences_merge_so_a_page_keeps_the_others(client, admin_headers):
    me = "/api/v1/users/me"
    await client.patch(
        me,
        json={"preferences": {"data_columns": {"hidden": ["code"], "shown": []}}},
        headers=admin_headers,
    )
    saved = await client.patch(
        me, json={"preferences": {"analysis_log_scale": ["ea_views.d28"]}}, headers=admin_headers
    )
    preferences = saved.json()["preferences"]
    assert preferences["data_columns"]["hidden"] == ["code"]
    assert preferences["analysis_log_scale"] == ["ea_views.d28"]


async def test_viewers_land_on_analysis_on_a_new_install(client, make_user):
    await make_user("reader@example.org", "reader-password-1", UserRole.viewer)
    body = await sign_in(client, "reader@example.org", "reader-password-1")
    assert body["user"]["landing"] == "analysis"


async def test_analysis_is_a_landing_choice(client, admin_headers, make_user):
    await make_user("someone@example.org", "someone-password-1", UserRole.editor)
    settings = (await client.get("/api/v1/settings/institution", headers=admin_headers)).json()
    response = await client.patch(
        "/api/v1/settings/institution",
        json={
            "field": "landing_pages",
            "value": {"admin": "mine", "editor": "analysis", "viewer": "all"},
            "version": settings["field_versions"].get("landing_pages", 0),
        },
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    body = await sign_in(client, "someone@example.org", "someone-password-1")
    assert body["user"]["landing"] == "analysis"
