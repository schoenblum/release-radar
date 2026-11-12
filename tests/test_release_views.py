"""The Data page's views (step 1.6): filters, search and the export. Synthetic data."""

import csv
import io
import re
from datetime import UTC, datetime, time

import openpyxl
import pytest
from sqlalchemy import select

from app.database import SessionLocal
from app.models import (
    CustomField,
    Institution,
    Release,
    Researcher,
    ResearchField,
    Unit,
    User,
    UserRole,
    Writer,
)

URL = "/api/v1/releases"
EXPORT = "/api/v1/releases/export"


async def _institution_id():
    async with SessionLocal() as db:
        return await db.scalar(select(Institution.id).order_by(Institution.created_at))


async def _add(*rows):
    async with SessionLocal() as db:
        db.add_all(rows)
        await db.commit()
    return rows


async def _create(client, headers, title, **fields):
    response = await client.post(URL, headers=headers, json={"title": title})
    assert response.status_code == 201, response.text
    release = response.json()
    for name, value in fields.items():
        response = await client.patch(
            f"{URL}/{release['id']}",
            headers=headers,
            json={"field": name, "value": value, "version": release["field_versions"].get(name, 0)},
        )
        assert response.status_code == 200, response.text
        release = response.json()["release"]
    return release


async def _list(client, headers, **params):
    response = await client.get(URL, headers=headers, params={"limit": 500, **params})
    assert response.status_code == 200, response.text
    return response.json()


def _titles(page) -> set[str]:
    return {item["title"] for item in page["items"]}


@pytest.fixture
async def lists():
    """Two units in two fields, two writers and two researchers with a shared surname."""
    institution_id = await _institution_id()
    stem = ResearchField(institution_id=institution_id, name_en="Sciences", name_ja="理系")
    hss = ResearchField(institution_id=institution_id, name_en="Humanities", name_ja="文系")
    await _add(stem, hss)
    north = Unit(
        institution_id=institution_id,
        key="North",
        name_en="North School",
        name_ja="北研究科",
        unit_type="school",
        default_field_id=stem.id,
    )
    south = Unit(
        institution_id=institution_id,
        key="South",
        name_en="South Institute",
        name_ja="南研究所",
        unit_type="institute",
        default_field_id=hss.id,
    )
    await _add(north, south)
    ada = Researcher(
        institution_id=institution_id, name="Ada Example", name_ja="例 エイダ", gender="F"
    )
    bo = Researcher(institution_id=institution_id, name="Bo Example")
    one = Writer(institution_id=institution_id, display_name_en="Writer One", display_name_ja="一")
    two = Writer(institution_id=institution_id, display_name_en="Writer Two")
    await _add(ada, bo, one, two)
    return {
        "stem": stem.id,
        "hss": hss.id,
        "north": north.id,
        "south": south.id,
        "ada": ada.id,
        "bo": bo.id,
        "one": one.id,
        "two": two.id,
    }


@pytest.fixture
async def three(client, admin_headers, lists):
    """Three releases across two academic years, units, writers and researchers."""
    first = await _create(
        client,
        admin_headers,
        "Quantum frogs",
        release_date="2026-03-31",
        unit_id=str(lists["north"]),
        researcher_id=str(lists["ada"]),
        writer_id=str(lists["one"]),
        doi="10.1234/frogs.1",
    )
    second = await _create(
        client,
        admin_headers,
        "Medieval maps",
        release_date="2026-04-01",
        unit_id=str(lists["south"]),
        researcher_id=str(lists["bo"]),
        writer_id=str(lists["two"]),
        notes="EA top page",
    )
    draft = await _create(client, admin_headers, "Untitled 100% idea")
    return first, second, draft


# ---------------------------------------------------------------- filters


async def test_each_filter_narrows_the_view_and_both_counts_are_given(
    client, admin_headers, lists, three
):
    everything = await _list(client, admin_headers)
    assert everything["total"] == everything["view_total"] == 3
    # From the release dates and the April start: 2026-03-31 is still AY2025.
    assert everything["academic_years"] == [2026, 2025]

    assert _titles(await _list(client, admin_headers, academic_year=2025)) == {"Quantum frogs"}
    assert _titles(await _list(client, admin_headers, academic_year=2026)) == {"Medieval maps"}
    # The field followed the unit (D7).
    assert _titles(await _list(client, admin_headers, field_id=lists["hss"])) == {"Medieval maps"}
    assert _titles(await _list(client, admin_headers, unit_id=lists["north"])) == {"Quantum frogs"}
    assert _titles(await _list(client, admin_headers, researcher_id=lists["bo"])) == {
        "Medieval maps"
    }
    narrowed = await _list(client, admin_headers, writer_id=lists["one"])
    assert _titles(narrowed) == {"Quantum frogs"}
    assert (narrowed["total"], narrowed["view_total"]) == (1, 3)
    # The draft was made by someone with no writer entry, so it has no writer yet.
    waiting = await _list(client, admin_headers, writer_id="none")
    assert _titles(waiting) == {"Untitled 100% idea"}
    bad = await client.get(URL, headers=admin_headers, params={"writer_id": "nobody"})
    assert bad.status_code == 422

    both = await _list(client, admin_headers, unit_id=lists["north"], academic_year=2026)
    assert both["items"] == [] and both["total"] == 0


async def test_a_year_needs_a_release_date_and_follows_the_start_month(
    client, admin_headers, three
):
    async with SessionLocal() as db:
        institution = await db.scalar(select(Institution))
        institution.ay_start_month = 1
        await db.commit()
    page = await _list(client, admin_headers, academic_year=2026)
    # With a January start both dated releases are in 2026, and the draft is in none.
    assert _titles(page) == {"Quantum frogs", "Medieval maps"}
    assert page["academic_years"] == [2026]


async def test_filters_apply_within_mine(client, headers_for, lists):
    headers = await headers_for(UserRole.editor, "writer@example.org")
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == "writer@example.org"))
        writer = await db.get(Writer, lists["one"])
        writer.user_id = user.id
        await db.commit()
    await _create(client, headers, "My north one", unit_id=str(lists["north"]))
    await _create(client, headers, "My south one", unit_id=str(lists["south"]))
    await _create(client, headers, "Someone else's", writer_id=str(lists["two"]))

    page = await _list(client, headers, view="mine", unit_id=lists["north"])
    assert _titles(page) == {"My north one"}
    assert (page["total"], page["view_total"]) == (1, 2)


async def test_an_unknown_year_or_id_is_refused_or_finds_nothing(client, admin_headers, three):
    response = await client.get(URL, headers=admin_headers, params={"academic_year": "soon"})
    assert response.status_code == 422
    response = await client.get(URL, headers=admin_headers, params={"unit_id": "not-an-id"})
    assert response.status_code == 422
    nothing = await _list(client, admin_headers, unit_id="00000000-0000-0000-0000-000000000000")
    assert nothing["items"] == []


# ---------------------------------------------------------------- search


@pytest.mark.parametrize(
    ("words", "found"),
    [
        ("frogs", {"Quantum frogs"}),
        ("QUANTUM", {"Quantum frogs"}),
        # Every word must match, each anywhere.
        ("quantum maps", set()),
        ("example maps", {"Medieval maps"}),
        # The researcher's names, in either language.
        ("Ada", {"Quantum frogs"}),
        ("エイダ", {"Quantum frogs"}),
        # A DOI as a link, and the code.
        ("https://doi.org/10.1234/FROGS.1", {"Quantum frogs"}),
        ("AY2025-01", {"Quantum frogs"}),
        # Notes, and full-width letters as typed with a Japanese input method.
        ("top page", {"Medieval maps"}),
        ("ｆｒｏｇｓ", {"Quantum frogs"}),
        # A percent sign is a character, not a wildcard.
        ("100%", {"Untitled 100% idea"}),
        ("%", {"Untitled 100% idea"}),
    ],
)
async def test_search_finds_every_word_anywhere(client, admin_headers, three, words, found):
    assert _titles(await _list(client, admin_headers, q=words)) == found


async def test_search_leaves_removed_releases_out(client, admin_headers, three):
    first = three[0]
    assert (await client.delete(f"{URL}/{first['id']}", headers=admin_headers)).status_code == 204
    assert _titles(await _list(client, admin_headers, q="frogs")) == set()


# ---------------------------------------------------------------- export


async def _export(client, headers, **body):
    response = await client.post(EXPORT, headers=headers, json=body)
    assert response.status_code == 200, response.text
    return response


def _sheet_rows(sheet) -> list[list]:
    return [[cell.value for cell in row] for row in sheet.iter_rows()]


def _by_header(rows: list[list]) -> list[dict]:
    header = rows[0]
    return [dict(zip(header, row, strict=True)) for row in rows[1:]]


async def _fill_numbers(client, headers, release):
    """An EurekAlert link opens day-28 views, which then get a number."""
    response = await client.patch(
        f"{URL}/{release['id']}",
        headers=headers,
        json={
            "field": "ea_url",
            "value": "https://www.eurekalert.org/news-releases/1",
            "version": release["field_versions"].get("ea_url", 0),
        },
    )
    release = response.json()["release"]
    reading = next(r for r in release["readings"] if r["measure_key"] == "ea_views.d28")
    response = await client.patch(
        f"/api/v1/readings/{reading['id']}",
        headers=headers,
        json={"value": "1,234", "version": reading["version"]},
    )
    assert response.status_code == 200, response.text


async def test_anyone_signed_in_may_export_and_nobody_else(client, headers_for, three):
    assert (await client.post(EXPORT, json={})).status_code == 401
    viewer = await headers_for(UserRole.viewer)
    response = await _export(client, viewer)
    assert "spreadsheetml" in response.headers["content-type"]
    assert 'filename="release_radar_releases_' in response.headers["content-disposition"]


async def test_the_workbook_has_releases_lists_and_a_read_me(client, admin_headers, three):
    first = three[0]
    await _fill_numbers(client, admin_headers, first)
    async with SessionLocal() as db:
        owner = await db.scalar(select(User).where(User.email == "chief@example.org"))
        owner.full_name = "Chief Example"
        db.add(
            CustomField(
                institution_id=owner.institution_id,
                key="clicks",
                label_en="Clicks",
                field_type="integer",
                scope="personal",
                owner_id=owner.id,
            )
        )
        release = await db.get(Release, first["id"])
        release.custom_values = {"clicks": {"state": "value", "value": 12}}
        release.release_time = time(14, 0)
        release.embargoed = True
        await db.commit()

    response = await _export(client, admin_headers, filters={"view": "all"})
    workbook = openpyxl.load_workbook(io.BytesIO(response.content))
    assert workbook.sheetnames == ["Releases", "Units", "Fields", "Read me"]

    rows = _by_header(_sheet_rows(workbook["Releases"]))
    assert list(rows[0])[:4] == ["Code", "Academic year", "Release date", "Title"]
    frogs = next(row for row in rows if row["Title"] == "Quantum frogs")
    assert frogs["Code"] == "AY2025-01"
    # Whatever can be a number is one, so nothing needs converting afterwards.
    assert frogs["Academic year"] == 2025
    assert frogs["Release date"].date().isoformat() == "2026-03-31"
    assert frogs["Release time (JST)"] == time(14, 0)
    assert frogs["Unit"] == "North School"
    assert frogs["Field"] == "Sciences"
    assert frogs["Researcher"] == "Ada Example"
    assert frogs["Researcher gender"] == "Female"
    assert frogs["Writer"] == "Writer One"
    assert frogs["Embargoed"] == 1
    assert frogs["EurekAlert top page"] == 0
    # A number, N/A where it cannot exist, and empty where it is still missing.
    assert frogs["EurekAlert views, day 28"] == 1234
    assert frogs["Altmetric score, day 0"] is None
    # A colleague's personal field carries its owner's name.
    assert frogs["Clicks (Chief Example)"] == 12
    draft = next(row for row in rows if row["Title"] == "Untitled 100% idea")
    assert draft["Code"] is None and draft["Academic year"] is None
    assert draft["Researcher gender"] is None
    assert draft["EurekAlert embargoed views"] == "N/A"
    medieval = next(row for row in rows if row["Title"] == "Medieval maps")
    assert medieval["Researcher gender"] == "Not recorded"
    headers = list(rows[0])
    assert headers.index("Researcher gender") == headers.index("Researcher") + 1
    assert headers.index("Publication date") == headers.index("DOI") + 1

    units = _by_header(_sheet_rows(workbook["Units"]))
    assert {(u["Name"], u["Type"], u["Default field"], u["Active"]) for u in units} == {
        ("North School", "School", "Sciences", 1),
        ("South Institute", "Institute", "Humanities", 1),
    }
    assert {row["Name"] for row in _by_header(_sheet_rows(workbook["Fields"]))} == {
        "Sciences",
        "Humanities",
    }
    notes = "\n".join(str(row[0] or "") for row in _sheet_rows(workbook["Read me"]))
    assert "3 in all" in notes
    assert "Shown: All." in notes
    assert "1 means yes, 0 means no" in notes
    # The example year is the current one, with the institution's April start.
    assert re.search(r"so (\d{4}) runs from \1-04 to \d{4}-03\.", notes)
    assert "personal data" in notes


async def test_an_inferred_day0_is_a_zero_with_a_column_saying_so(client, admin_headers, three):
    """R8.1.3: the 0 as a number, a 1 in the column beside it, and a line in the Read me."""
    async with SessionLocal() as db:
        release = await db.get(Release, three[0]["id"])
        release.doi = "10.1234/inferred"
        release.publication_date = release.release_date
        await db.commit()

    response = await _export(client, admin_headers, filters={"view": "all"})
    workbook = openpyxl.load_workbook(io.BytesIO(response.content))
    rows = _by_header(_sheet_rows(workbook["Releases"]))
    headers = list(rows[0])
    assert headers.index("Altmetric score, day 0 inferred") == (
        headers.index("Altmetric score, day 0") + 1
    )
    frogs = next(row for row in rows if row["Title"] == "Quantum frogs")
    assert (frogs["Altmetric score, day 0"], frogs["Altmetric score, day 0 inferred"]) == (0, 1)
    others = [row for row in rows if row["Title"] != "Quantum frogs"]
    assert {row["Altmetric score, day 0 inferred"] for row in others} == {0}
    notes = "\n".join(str(row[0] or "") for row in _sheet_rows(workbook["Read me"]))
    assert "the 0 before it was not entered" in notes

    japanese = await _export(client, admin_headers, language="ja", filters={"view": "all"})
    header = _sheet_rows(openpyxl.load_workbook(io.BytesIO(japanese.content)).worksheets[0])[0]
    assert any(str(name).endswith("（推定）") for name in header)


async def test_the_workbook_in_japanese(client, admin_headers, lists, three):
    response = await _export(
        client,
        admin_headers,
        language="ja",
        filters={
            "view": "all",
            "unit_id": str(lists["north"]),
            "q": "frogs",
            "academic_year": 2025,
        },
    )
    workbook = openpyxl.load_workbook(io.BytesIO(response.content))
    assert workbook.sheetnames == ["リリース", "部局", "分野", "はじめにお読みください"]
    rows = _by_header(_sheet_rows(workbook["リリース"]))
    assert len(rows) == 1
    row = rows[0]
    assert row["年度"] == 2025
    assert row["部局"] == "北研究科"
    assert row["分野"] == "理系"
    assert row["研究者"] == "例 エイダ"
    assert row["ライター"] == "一"
    assert row["エンバーゴあり"] == 0
    assert row["研究者の性別"] == "女性"
    # Not embargoed, so embargoed views cannot exist.
    assert "該当なし" in row.values()
    # Free text stays as written (R5.4.5).
    assert row["タイトル"] == "Quantum frogs"
    notes = "\n".join(str(r[0] or "") for r in _sheet_rows(workbook["はじめにお読みください"]))
    assert "すべて、2025年度、北研究科、「frogs」で検索" in notes


async def test_a_relabelled_field_is_exported_under_its_new_name(client, admin_headers, three):
    fields = (await client.get("/api/v1/core-fields", headers=admin_headers)).json()
    title = next(field for field in fields if field["key"] == "title")
    response = await client.patch(
        f"/api/v1/core-fields/{title['id']}",
        headers=admin_headers,
        json={"field": "label_en", "value": "Headline", "version": 0},
    )
    assert response.status_code == 200, response.text
    workbook = openpyxl.load_workbook(io.BytesIO((await _export(client, admin_headers)).content))
    assert "Headline" in _sheet_rows(workbook["Releases"])[0]


async def test_gender_leaves_the_export_when_settings_hide_it(client, admin_headers, three):
    fields = (await client.get("/api/v1/core-fields", headers=admin_headers)).json()
    gender = next(field for field in fields if field["key"] == "researcher_gender")
    assert gender["can_require"] is False
    response = await client.patch(
        f"/api/v1/core-fields/{gender['id']}",
        headers=admin_headers,
        json={"field": "in_record", "value": False, "version": 0},
    )
    assert response.status_code == 200, response.text
    # Still in the grid by default: still in use, so still exported.
    workbook = openpyxl.load_workbook(io.BytesIO((await _export(client, admin_headers)).content))
    assert "Researcher gender" in _sheet_rows(workbook["Releases"])[0]
    response = await client.patch(
        f"/api/v1/core-fields/{gender['id']}",
        headers=admin_headers,
        json={"field": "in_grid", "value": False, "version": 0},
    )
    assert response.status_code == 200, response.text
    workbook = openpyxl.load_workbook(io.BytesIO((await _export(client, admin_headers)).content))
    assert "Researcher gender" not in _sheet_rows(workbook["Releases"])[0]
    refused = await client.patch(
        f"/api/v1/core-fields/{gender['id']}",
        headers=admin_headers,
        json={"field": "required", "value": True, "version": 0},
    )
    assert refused.status_code == 409


async def test_the_view_follows_the_filters_and_the_order_on_screen(
    client, admin_headers, lists, three
):
    first, second, draft = three
    removed = await _create(client, admin_headers, "Gone", unit_id=str(lists["north"]))
    await client.delete(f"{URL}/{removed['id']}", headers=admin_headers)

    response = await _export(
        client, admin_headers, format="csv", order=[second["id"], draft["id"], first["id"]]
    )
    rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))
    assert [row[3] for row in rows[1:]] == ["Medieval maps", "Untitled 100% idea", "Quantum frogs"]

    response = await _export(
        client, admin_headers, format="csv", filters={"unit_id": str(lists["north"])}
    )
    rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))
    assert [row[3] for row in rows[1:]] == ["Quantum frogs"]


async def test_csv_is_utf8_with_a_bom_and_keeps_formulas_as_text(client, admin_headers):
    await _create(client, admin_headers, "=HYPERLINK(1)", also_featured="日本語の名前")
    response = await _export(client, admin_headers, format="csv", language="ja")
    assert response.content.startswith(b"\xef\xbb\xbf")
    assert response.headers["content-type"].startswith("text/csv")
    rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))
    assert rows[0][:4] == ["コード", "年度", "リリース日", "タイトル"]
    assert rows[1][3] == "'=HYPERLINK(1)"
    assert "日本語の名前" in rows[1]


async def test_xlsx_keeps_formulas_as_text(client, admin_headers):
    await _create(client, admin_headers, "=SUM(A1:A9)")
    workbook = openpyxl.load_workbook(io.BytesIO((await _export(client, admin_headers)).content))
    cell = workbook["Releases"]["D2"]
    assert cell.value == "=SUM(A1:A9)" and cell.data_type == "s"


async def test_another_institutions_releases_never_reach_a_file(client, admin_headers):
    async with SessionLocal() as db:
        other = Institution(name_en="Elsewhere", timezone="UTC", settings={})
        db.add(other)
        await db.flush()
        db.add(Release(institution_id=other.id, title="Not ours"))
        ours = await db.scalar(select(Institution.id).order_by(Institution.created_at))
        db.add(Release(institution_id=ours, title="Ours", deleted_at=datetime.now(UTC)))
        await db.commit()
    response = await _export(client, admin_headers, format="csv")
    text = response.content.decode("utf-8-sig")
    assert "Not ours" not in text and "Ours" not in text
