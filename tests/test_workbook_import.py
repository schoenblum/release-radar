"""Import of the old workbook (step 1.8). Synthetic workbooks in the real one's shape."""

import base64
import io
from datetime import date, datetime, time
from decimal import Decimal

import openpyxl
import pytest
from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import (
    AuditLog,
    CustomField,
    Institution,
    Measure,
    Reading,
    Release,
    Researcher,
    ResearchField,
    Unit,
    UserRole,
    Writer,
)
from app.services import crossref
from app.services.workbook_import import importer
from app.services.workbook_import.values import (
    read_count,
    read_date,
    read_gender,
    read_text,
    read_time,
    split_names,
    top_page,
)

URL = "/api/v1/imports/workbook"
DOMAIN = "en.example.org"
EA = "https://www.eurekalert.org/news-releases/"

GROUPS = [
    None, "Press release", None, None, None, "Dates", None, None, "Paper", None, None,
    "EurekAlert", None, None, None, None, "Altmetrics", None, None, None, "URLs", None,
    "Bitly", "Pitches", "NOTES",
]  # fmt: skip
HEADINGS = [
    "ID", "Title", "Writer", "School", "Researcher", "Request received",
    "First author (M/F)", "Embargo", "Title", "DOI", "Embargoed views", "Release posted",
    "Time (ET)", "1 day", "7 day", "28 day", "0 day", "1 day score", "7 day score",
    "28 day score", "EurekAlert", "Website", "28 day engagements", None, None,
]  # fmt: skip
COLUMNS = [
    "code", "title", "writer", "unit", "researcher", "request_received", "gender", "embargo",
    "paper_title", "doi", "ea_views_d0", "release_date", "release_time", "ea_1", "ea_7",
    "ea_views_d28", "altmetric_d0", "alt_1", "alt_7", "altmetric_d28", "ea_url",
    "website_url", "bitly", "pitches", "notes",
]  # fmt: skip


def _release(**cells):
    base = {
        "writer": "Ada",
        "unit": "Science",
        "gender": "F",
        "release_date": datetime(2025, 5, 1),
        "website_url": f"https://{DOMAIN}/news/1",
    }
    return {**base, **cells}


ROWS = [
    _release(
        code="AY2025-01",
        title="  Frogs sing in the rain ",
        researcher="Kim Example",
        request_received=datetime(2025, 4, 1),
        embargo=datetime(2025, 4, 28),
        paper_title="A paper on frogs",
        doi="10.1234/frogs.",
        ea_views_d0=120,
        release_time=time(0, 10),
        ea_1=5,
        ea_views_d28=1500,
        altmetric_d0="-",
        altmetric_d28="12",
        ea_url=f" {EA}1001",
        bitly=40,
        pitches=3,
        notes="EA front page: Top spot No.2",
    ),
    _release(
        code="AY2025-02",
        title="Salt in space",
        writer="bo",
        unit="SCI",
        researcher="Tanaka",
        gender="\nM",
        request_received="23-Jan-2026",
        doi="DOI: https://doi.org/10.1234/SALT",
        release_date="4-March-26",
        release_time="  0:15",
        ea_views_d28="#REF!",
        altmetric_d0=5,
        altmetric_d28=datetime(1900, 1, 10),
        ea_url=f"{EA}1002",
        website_url="https://www.example.org/researchinfo/2",
        bitly="-",
    ),
    _release(
        code="AY2025-02",
        title="Maps of moss",
        researcher="Lee Example and Max Other",
        doi="10.1234/moss",
        ea_views_d28="805",
        ea_url=f"{EA}1003",
    ),
    _release(
        code="AY2025-05",
        title="Two people, one release",
        researcher="Pat One, Pat Two",
        doi="10.1234/two",
        ea_url=f"{EA}1005",
    ),
    _release(code="AY2025-06", title="Written by a unit", writer="Medicine", doi="10.1234/unit"),
    _release(
        code="AY2025-07",
        title="Nothing known yet",
        researcher=None,
        gender="-",
        embargo="-",
        ea_views_d0="-",
        release_date="-",
        doi="N/A",
        ea_url="-",
    ),
]


def release_list(rows=ROWS) -> bytes:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "PR DATA"
    for column, (group, heading) in enumerate(zip(GROUPS, HEADINGS, strict=True), start=1):
        sheet.cell(1, column, group)
        sheet.cell(2, column, heading)
    for number, row in enumerate(rows, start=3):
        for column, name in enumerate(COLUMNS, start=1):
            sheet.cell(number, column, row.get(name))
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def intake(*, override: str | None = "Pat Two") -> bytes:
    workbook = openpyxl.Workbook()
    staff = workbook.active
    staff.title = "Staff"
    staff.append(
        ["Name in workbook", "Releases in workbook", "Full name", "Email",
         "Writes releases (Y/N)", "App role", "Notes"]
    )  # fmt: skip
    staff.append(["Ada", 4, "Ada Writer", "ada@example.org", "Y", "editor", None])
    staff.append(["Bo", 3, "Bo Former", None, "N", None, "Has left"])
    staff.append(["Cy", None, "Cy Viewer", "cy@example.org", "N", "viewer", None])
    units = workbook.create_sheet("Units")
    units.append(
        ["Value in workbook", "Releases in workbook", "Official name (EN)", "Name (JA)",
         "Short label (charts)", "Type", "Aliases (comma-separated)", "Active (Y/N)"]
    )  # fmt: skip
    units.append(
        ["Science", 4, "Graduate School of Science", "理学研究科", "Science", None, "SCI", "Y"]
    )
    units.append(
        ["Medicine", 1, "Graduate School of Medicine", "医学系研究科", "Medicine", None, None, "Y"]
    )
    units.append(["Release counts include the alias spellings found in the data.", *[None] * 7])
    fields = workbook.create_sheet("Fields")
    fields.append(["Field (EN)", "Field (JA)", "Scope / what belongs here"])
    fields.append(["STEM", "理系", "Science\nMedicine"])
    fields.append(
        ["Starter suggestion only (not from your data). One field per release.", None, None]
    )
    two = workbook.create_sheet("Two-name releases")
    two.append(
        ["ID", "Release title", "Researcher as recorded", "Gender as recorded",
         "Proposed corresponding researcher (first listed)", "Override (only if wrong)",
         "Also featured (note only)"]
    )  # fmt: skip
    two.append(["AY2025-05", "Two people", "Pat One, Pat Two", "F", "Pat One", override, "Pat One"])
    two.append(["AY2025 rows use surnames only; resolved from the paper's authors.", *[None] * 6])
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _file(name: str, content: bytes) -> dict:
    return {"name": name, "content": base64.b64encode(content).decode()}


def _body(commit=False, owners=None, files=None, language="en", **extra):
    list_bytes, intake_bytes = files or (release_list(), intake())
    return {
        "release_list": _file("Press release list.xlsx", list_bytes),
        "intake": _file("Release Radar intake.xlsx", intake_bytes),
        "owners": owners or {},
        "commit": commit,
        "language": language,
        **extra,
    }


@pytest.fixture(autouse=True)
async def setting(crossref_answers):
    """A website domain, Crossref answering for two papers, and no answers kept from before."""
    importer._crossref_cache.clear()
    async with SessionLocal() as db:
        institution = await db.scalar(select(Institution).order_by(Institution.created_at))
        institution.website_domain = DOMAIN
        await db.commit()
    crossref_answers["status"] = 404
    crossref_answers["works"] = {
        "10.1234/frogs": {
            "title": ["Frogs, in full"],
            "container-title": ["Journal of Frogs"],
            "published": {"date-parts": [[2025, 3, 3]]},
            "author": [{"given": "Kim", "family": "Example"}],
        },
        "10.1234/salt": {
            "title": ["Salt"],
            "container-title": ["Space Letters"],
            "published": {"date-parts": [[2026, 2, 2]]},
            "author": [
                {"given": "Hana", "family": "Tanaka"},
                {"given": "Ken", "family": "Other"},
            ],
        },
    }
    return crossref_answers


async def _post(client, headers, **body):
    response = await client.post(URL, headers=headers, json=_body(**body))
    assert response.status_code == 200, response.text
    return response.json()


async def _releases() -> dict[str, Release]:
    async with SessionLocal() as db:
        return {release.code: release for release in await db.scalars(select(Release))}


async def _readings(release_id) -> dict[str, Reading]:
    async with SessionLocal() as db:
        rows = await db.execute(
            select(Measure.key, Reading)
            .join(Reading, Reading.measure_id == Measure.id)
            .where(Reading.release_id == release_id)
        )
        return {key: reading for key, reading in rows.all()}


# ---------------------------------------------------------------- reading cells


@pytest.mark.parametrize(
    ("cell", "expected", "how"),
    [
        (datetime(2025, 4, 1, 0, 0), date(2025, 4, 1), "native"),
        ("4-March-26", date(2026, 3, 4), "text"),
        ("9-Apr-26", date(2026, 4, 9), "text"),
        ("23-Jan-2026", date(2026, 1, 23), "text"),
        ("2026/1/5", date(2026, 1, 5), "text"),
        ("2026年1月5日", date(2026, 1, 5), "text"),
        ("-", None, "dash"),
        ("", None, "empty"),
        ("31-Sept-25", None, "invalid"),
        ("soon", None, "invalid"),
    ],
)
def test_reading_dates(cell, expected, how):
    read = read_date(cell)
    assert (read.value, read.how) == (expected, how)


@pytest.mark.parametrize(
    ("cell", "expected", "how"),
    [
        (1500, Decimal("1500"), "native"),
        ("805", Decimal("805"), "text"),
        ("1,234", Decimal("1234"), "text"),
        ("-", None, "dash"),
        ("N/A", None, "dash"),
        (None, None, "empty"),
        ("#REF!", None, "invalid"),
        ("*601", None, "invalid"),
        (datetime(2026, 11, 24), None, "invalid"),
        (-3, None, "invalid"),
    ],
)
def test_reading_numbers(cell, expected, how):
    read = read_count(cell)
    assert (read.value, read.how) == (expected, how)


def test_reading_times_genders_names_and_the_top_page():
    assert read_time("  0:10").value == time(0, 10)
    assert read_time(time(3, 15, 40)).value == time(3, 15)
    assert read_time("25:00").how == "invalid"
    assert read_gender("\nM").value == "M"
    assert read_gender("-").how == "dash"
    assert read_gender("X").how == "invalid"
    assert read_text("  a  b ").value == "a b"
    assert split_names("Lee Example and Max Other") == ("Lee Example", ["Max Other"])
    assert split_names("Pat One, Pat Two, Sam Three") == ("Pat One", ["Pat Two", "Sam Three"])
    assert top_page("EA front page") == (True, None)
    assert top_page("EA top page") == (True, None)
    assert top_page("EA front page: Top spot") == (True, 1)
    assert top_page("EA front page: Top spot No.2 - Joint PR") == (True, 2)
    assert top_page("Feature story 1") == (False, None)


@pytest.mark.parametrize(
    ("text", "doi"),
    [
        ("10.1234/ABC.", "10.1234/abc"),
        ("DOI: https://doi.org/10.1234/abc", "10.1234/abc"),
        ("https://dx.doi.org/10.1234/abc;", "10.1234/abc"),
        ("N/A", None),
    ],
)
def test_dois_copied_from_a_paper_are_forgiven(text, doi):
    assert crossref.normalise_doi(text) == doi


# ---------------------------------------------------------------- dry run and import


async def test_only_admins_may_import(client, headers_for):
    editor = await headers_for(UserRole.editor)
    response = await client.post(URL, headers=editor, json=_body())
    assert response.status_code == 403
    assert (await client.post(URL, json=_body())).status_code == 401


async def test_a_dry_run_changes_nothing_and_says_what_would_happen(client, admin_headers):
    result = await _post(client, admin_headers)
    assert result["committed"] is False
    counts = result["counts"]
    assert counts["releases_in_workbook"] == 6
    assert counts["releases_skipped"] == 1
    assert counts["releases_new"] == 5
    assert counts["units_new"] == 2 and counts["fields_new"] == 1
    assert counts["writers_new"] == 2
    assert counts["crossref_found"] == 2
    assert result["filename"].startswith("release_radar_dry_run_")
    assert "dry run" in result["markdown"]
    assert await _releases() == {}
    async with SessionLocal() as db:
        assert await db.scalar(select(func.count()).select_from(Unit)) == 0
        assert await db.scalar(select(func.count()).select_from(Researcher)) == 0


async def test_the_import_brings_everything_in(client, admin_headers, make_user):
    ada = await make_user("ada@example.org", role=UserRole.editor)
    owner = await make_user("owner@example.org", role=UserRole.editor)
    result = await _post(
        client,
        admin_headers,
        commit=True,
        owners={
            "bitly": str(owner.id),
            "pitches": str(owner.id),
            "request_received": str(owner.id),
        },
    )
    assert result["committed"] is True
    releases = await _releases()
    # Written by a unit, so skipped; the second AY2025-02 got the next free number, after the
    # highest code in the workbook.
    assert set(releases) == {"AY2025-01", "AY2025-02", "AY2025-05", "AY2025-07", "AY2025-08"}

    async with SessionLocal() as db:
        units = {unit.key: unit for unit in await db.scalars(select(Unit))}
        stem = await db.scalar(select(ResearchField))
        writers = {writer.display_name_en: writer for writer in await db.scalars(select(Writer))}
        people = {person.name: person for person in await db.scalars(select(Researcher))}
        fields = {field.label_en: field for field in await db.scalars(select(CustomField))}
        note = await db.scalar(
            select(AuditLog.note).where(AuditLog.entity_id == releases["AY2025-01"].id)
        )
    assert units["Science"].aliases == ["SCI"] and units["Science"].name_ja == "理学研究科"
    assert units["Science"].default_field_id == stem.id and stem.name_ja == "理系"
    assert writers["Ada"].user_id == ada.id and writers["Ada"].full_name == "Ada Writer"
    assert writers["Bo"].is_active is False
    assert "Cy" not in writers
    assert note == "workbook_import"

    frogs = releases["AY2025-01"]
    assert frogs.title == "Frogs sing in the rain"
    assert frogs.writer_id == writers["Ada"].id
    assert frogs.unit_id == units["Science"].id and frogs.field_id == stem.id
    assert frogs.doi == "10.1234/frogs"
    assert frogs.paper_title == "A paper on frogs"
    assert (frogs.journal, frogs.publication_date) == ("Journal of Frogs", date(2025, 3, 3))
    assert frogs.embargoed is True
    assert (frogs.release_date, frogs.release_time_et) == (date(2025, 5, 1), time(0, 10))
    assert frogs.ea_url == f"{EA}1001"
    assert (frogs.ea_top_page, frogs.ea_top_position) == (True, 2)
    assert frogs.notes == "EA front page: Top spot No.2"
    kim = people["Kim Example"]
    assert (kim.gender, kim.status, kim.current_unit_id) == ("F", "unverified", units["Science"].id)
    readings = await _readings(frogs.id)
    assert readings["ea_views.d0"].value == 120
    assert readings["ea_views.d28"].value == 1500
    assert (readings["altmetric.d0"].state, readings["altmetric.d0"].source) == (
        "not_applicable",
        "manual",
    )
    assert readings["altmetric.d28"].value == 12
    assert readings["hp_views.d28"].state == "missing"
    by_key = {field.key: field for field in fields.values()}
    assert frogs.custom_values == {
        fields["Bitly clicks, 28 days"].key: {"state": "value", "value": 40},
        fields["Pitches"].key: {"state": "value", "value": 3},
        fields["Request received"].key: {"state": "value", "value": "2025-04-01"},
    }
    assert all(field.owner_id == owner.id for field in by_key.values())
    assert fields["Bitly clicks, 28 days"].due_checkpoint_id is not None

    salt = releases["AY2025-02"]
    assert salt.unit_id == units["Science"].id  # through the alias
    assert salt.writer_id == writers["Bo"].id  # case aside
    assert salt.doi == "10.1234/salt"
    assert (salt.release_date, salt.release_time_et) == (date(2026, 3, 4), time(0, 15))
    assert salt.embargoed is False
    # A surname alone, settled by the paper's one author of that name.
    hana = people["Hana Tanaka"]
    assert (hana.given_name, hana.family_name, hana.status) == ("Hana", "Tanaka", "unverified")
    assert hana.gender == "M" and salt.researcher_id == hana.id
    salt_readings = await _readings(salt.id)
    assert salt_readings["ea_views.d28"].state == "missing"  # #REF!
    assert salt_readings["altmetric.d0"].value == 5
    assert salt_readings["altmetric.d28"].state == "missing"  # a 1900 date
    assert salt_readings["hp_views.d28"].state == "not_applicable"  # off the domain
    assert salt.custom_values[fields["Bitly clicks, 28 days"].key] == {"state": "not_applicable"}
    assert salt.custom_values[fields["Request received"].key]["value"] == "2026-01-23"

    moss = releases["AY2025-08"]
    assert moss.title == "Maps of moss" and moss.also_featured == "Max Other"
    assert people["Lee Example"].id == moss.researcher_id
    assert (await _readings(moss.id))["ea_views.d28"].value == 805

    two = releases["AY2025-05"]
    assert two.researcher_id == people["Pat Two"].id and two.also_featured == "Pat One"

    unknown = releases["AY2025-07"]
    assert unknown.researcher_id is None and unknown.release_date is None
    assert unknown.doi is None and unknown.ea_url is None and unknown.embargoed is False
    assert (await _readings(unknown.id))["ea_views.d0"].state == "not_applicable"

    markdown = result["markdown"]
    for text in (
        "Row 4 has this code too: this release gets AY2025-08.",
        "Written by a unit, not by the office: not imported.",
        "probably the number 10 formatted as a date",
        "read as Hana Tanaka",
        "Read as the unit Science.",
        "Lee Example, the first, is the corresponding researcher",
        "Taken from the Two-name releases sheet: Pat Two.",
        "Means not applicable (the dash rule).",
        "Not on en.example.org",
        "Text read as the number 805.",
    ):
        assert text in markdown, text
    assert result["levels"]["check"] > 0
    assert result["csv"].splitlines()[0] == "Kind,Row,Code,Column,In the workbook,What happened"


async def test_importing_again_finds_everything_and_clears_nothing(client, admin_headers):
    await _post(client, admin_headers, commit=True)
    first = await _releases()
    async with SessionLocal() as db:
        moss = await db.get(Release, first["AY2025-08"].id)
        moss.notes = "Written in the app since"
        frogs = await db.get(Release, first["AY2025-01"].id)
        chosen = Researcher(institution_id=frogs.institution_id, name="Chosen In App")
        db.add(chosen)
        await db.flush()
        frogs.researcher_id = chosen.id
        await db.commit()

    result = await _post(client, admin_headers, commit=True)
    counts = result["counts"]
    assert counts.get("releases_new", 0) == 0
    assert counts["releases_unchanged"] + counts.get("releases_updated", 0) == 5
    again = await _releases()
    assert set(again) == set(first)
    # The second AY2025-02 is found by its EurekAlert link, not given yet another code.
    assert again["AY2025-08"].id == first["AY2025-08"].id
    # A note the workbook doesn't have stays; a researcher chosen in the app stays.
    assert again["AY2025-08"].notes == "Written in the app since"
    assert again["AY2025-01"].researcher_id == chosen.id
    async with SessionLocal() as db:
        assert await db.scalar(select(func.count()).select_from(Unit)) == 2
        assert await db.scalar(select(func.count()).select_from(Writer)) == 2
        names = list(await db.scalars(select(Researcher.name)))
    assert len(names) == len(set(names))


async def test_a_release_made_in_the_app_with_a_workbook_code_is_named(client, admin_headers):
    async with SessionLocal() as db:
        institution = await db.scalar(select(Institution).order_by(Institution.created_at))
        db.add(Release(institution_id=institution.id, code="AY2025-01", title="Made by hand"))
        await db.commit()
    result = await _post(client, admin_headers)
    assert "A release made in the app already has this code" in result["markdown"]


async def test_the_report_in_japanese(client, admin_headers):
    result = await _post(client, admin_headers, language="ja")
    assert "ワークブックのインポート：試行（変更なし）" in result["markdown"]
    assert result["csv"].startswith("種類,行,コード,列,ワークブックの値,結果")


@pytest.mark.parametrize(
    ("files", "detail"),
    [
        ((b"not a workbook", intake()), "import_not_a_workbook"),
        ((intake(), intake()), "import_sheet_missing"),
    ],
)
async def test_wrong_files_are_refused_in_plain_words(client, admin_headers, files, detail):
    response = await client.post(URL, headers=admin_headers, json=_body(files=files))
    assert response.status_code == 422
    assert response.json()["detail"] == detail


async def test_a_missing_column_is_named(client, admin_headers):
    workbook = openpyxl.load_workbook(io.BytesIO(release_list()))
    workbook["PR DATA"].cell(2, 10, "Digital object")
    buffer = io.BytesIO()
    workbook.save(buffer)
    response = await client.post(
        URL, headers=admin_headers, json=_body(files=(buffer.getvalue(), intake()))
    )
    assert response.status_code == 422
    assert response.json() == {"detail": "import_column_missing", "column": "DOI", "group": ""}


async def test_every_check_and_import_is_kept_with_its_report(client, admin_headers, headers_for):
    checked = await _post(client, admin_headers)
    imported = await _post(client, admin_headers, commit=True)
    response = await client.get("/api/v1/imports", headers=admin_headers)
    assert response.status_code == 200, response.text
    runs = response.json()
    assert [run["id"] for run in runs] == [imported["run_id"], checked["run_id"]]
    assert [run["committed"] for run in runs] == [True, False]
    assert runs[0]["file_names"] == ["Press release list.xlsx", "Release Radar intake.xlsx"]
    assert runs[0]["user_name"] == "chief@example.org"
    assert runs[0]["counts"]["releases_new"] == 5
    assert runs[0]["levels"]["check"] == imported["levels"]["check"]

    # The report can be read again later, in either language.
    markdown = await client.get(
        f"/api/v1/imports/{checked['run_id']}/report", headers=admin_headers
    )
    assert markdown.status_code == 200
    assert 'filename="release_radar_dry_run_' in markdown.headers["content-disposition"]
    assert "Row 4 has this code too: this release gets AY2025-08." in markdown.text
    csv_ja = await client.get(
        f"/api/v1/imports/{imported['run_id']}/report",
        headers=admin_headers,
        params={"format": "csv", "language": "ja"},
    )
    assert csv_ja.content.startswith(b"\xef\xbb\xbf")
    assert csv_ja.content.decode("utf-8-sig").startswith("種類,行,コード,列,ワークブックの値,結果")

    editor = await headers_for(UserRole.editor)
    assert (await client.get("/api/v1/imports", headers=editor)).status_code == 403
    missing = await client.get(
        "/api/v1/imports/00000000-0000-0000-0000-000000000000/report", headers=admin_headers
    )
    assert missing.status_code == 404


# ---------------------------------------------------------------- only filling what is empty


async def test_only_filling_what_is_empty_changes_nothing_already_there(client, admin_headers):
    """Phase-2 brief §3.4, the catch-up before D1: what was corrected in Release Radar stays,
    what is still empty there is filled, new codes come in full, and the report lists both."""
    from datetime import UTC

    await _post(client, admin_headers, commit=True)
    first = await _releases()
    async with SessionLocal() as db:
        frogs = await db.get(Release, first["AY2025-01"].id)
        frogs.doi = "10.1234/corrected"
        chosen = Researcher(institution_id=frogs.institution_id, name="Chosen In App")
        db.add(chosen)
        await db.flush()
        frogs.researcher_id = chosen.id
        (await db.get(Release, first["AY2025-02"].id)).ea_url = None
        (await db.get(Release, first["AY2025-05"].id)).deleted_at = datetime.now(UTC)
        await db.commit()
    frogs_views = (await _readings(first["AY2025-01"].id))["ea_views.d28"]
    moss_views = (await _readings(first["AY2025-08"].id))["ea_views.d28"]
    async with SessionLocal() as db:
        (await db.get(Reading, frogs_views.id)).value = Decimal(1400)
        moss = await db.get(Reading, moss_views.id)
        moss.value, moss.state, moss.source = None, "missing", "auto"
        await db.commit()

    rows = [
        *ROWS,
        _release(
            code="AY2025-09",
            title="New since",
            doi="10.1234/new",
            ea_url=f"{EA}1009",
            ea_views_d28=7,
        ),
    ]
    files = (release_list(rows), intake())
    check = await _post(client, admin_headers, files=files, fill_empty_only=True)
    assert (await _releases())["AY2025-01"].doi == "10.1234/corrected"
    result = await _post(client, admin_headers, files=files, fill_empty_only=True, commit=True)
    assert result["counts"] == check["counts"]

    again = await _releases()
    # Kept: a corrected DOI, a researcher chosen in the app, a typed number, a removal.
    assert again["AY2025-01"].doi == "10.1234/corrected"
    assert again["AY2025-01"].researcher_id == chosen.id
    assert (await _readings(again["AY2025-01"].id))["ea_views.d28"].value == Decimal(1400)
    assert again["AY2025-05"].deleted_at is not None
    # Filled: what was empty in Release Radar.
    assert again["AY2025-02"].ea_url == f"{EA}1002"
    assert (await _readings(again["AY2025-08"].id))["ea_views.d28"].value == Decimal(805)
    # New codes come in full.
    assert again["AY2025-09"].title == "New since"
    assert (await _readings(again["AY2025-09"].id))["ea_views.d28"].value == Decimal(7)

    markdown = result["markdown"]
    assert "Only what is empty in Release Radar is filled" in markdown
    assert "Release Radar has “10.1234/corrected” (doi): kept" in markdown
    assert "Release Radar has “Chosen In App” (researcher_id): kept" in markdown
    assert "Release Radar has “1400” (ea_views.d28): kept" in markdown
    assert "Empty in Release Radar (ea_url): filled" in markdown
    assert "Empty in Release Radar (ea_views.d28): filled" in markdown
    assert "Removed in the app: left as it is" in markdown
    assert result["counts"]["cells_filled"] >= 2
    assert result["counts"]["cells_kept"] >= 3
    # Nothing new was filled into the kept release: its history has no new entries.
    async with SessionLocal() as db:
        notes = list(
            await db.scalars(
                select(AuditLog.field).where(
                    AuditLog.entity_id == again["AY2025-01"].id, AuditLog.action == "update"
                )
            )
        )
    assert "doi" in notes  # the correction made in the app
    assert notes.count("doi") == 1


async def test_without_the_choice_the_workbook_still_wins(client, admin_headers):
    await _post(client, admin_headers, commit=True)
    first = await _releases()
    async with SessionLocal() as db:
        (await db.get(Release, first["AY2025-01"].id)).doi = "10.1234/corrected"
        await db.commit()
    await _post(client, admin_headers, commit=True)
    assert (await _releases())["AY2025-01"].doi == "10.1234/frogs"
