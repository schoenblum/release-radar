"""List editors and CSV import and export. Synthetic data."""

import pytest
from sqlalchemy import select

from app.database import SessionLocal
from app.models import AuditLog, Institution, ResearchField, User, UserRole, Writer

UNITS = "/api/v1/lists/units"
FIELDS = "/api/v1/lists/fields"
WRITERS = "/api/v1/lists/writers"
VOCABULARIES = "/api/v1/lists/vocabularies"


async def _create(client, url, headers, **values):
    return await client.post(url, headers=headers, json={"values": values})


async def _patch(client, url, headers, field, value, version=0):
    return await client.patch(
        url, headers=headers, json={"field": field, "value": value, "version": version}
    )


async def _import(client, url, headers, text, dry_run=False):
    return await client.post(url, headers=headers, json={"csv": text, "dry_run": dry_run})


# ---------------------------------------------------------------- who may do what


async def test_everyone_signed_in_can_read_the_lists_but_only_admins_change_them(
    client, headers_for
):
    admin = await headers_for(UserRole.admin)
    created = await _create(client, UNITS, admin, name_en="School of Testing")
    assert created.status_code == 201
    url = f"{UNITS}/{created.json()['id']}"

    for role in (UserRole.editor, UserRole.viewer):
        headers = await headers_for(role)
        assert (await client.get(UNITS, headers=headers)).status_code == 200
        assert (await _create(client, UNITS, headers, name_en="No")).status_code == 403
        assert (await _patch(client, url, headers, "name_ja", "No")).status_code == 403
        assert (await client.get(f"{UNITS}/export", headers=headers)).status_code == 403
        assert (await _import(client, f"{UNITS}/import", headers, "key\nx\n")).status_code == 403


async def test_an_unknown_list_does_not_exist(client, admin_headers):
    assert (await client.get("/api/v1/lists/nothing", headers=admin_headers)).status_code == 404


# ---------------------------------------------------------------- units and fields


async def test_a_unit_with_everything(client, admin_headers):
    field = (await _create(client, FIELDS, admin_headers, name_en="Sciences")).json()
    response = await _create(
        client,
        UNITS,
        admin_headers,
        name_en="School of Testing",
        name_ja="試験研究科",
        short_label="Testing",
        unit_type="school",
        aliases="TEST, Test School",
        default_field_id=field["id"],
    )
    assert response.status_code == 201
    unit = response.json()
    assert unit["key"] == "School of Testing"
    assert unit["aliases"] == ["TEST", "Test School"]
    assert unit["default_field_id"] == field["id"]
    assert unit["is_active"] is True


async def test_a_unit_needs_a_name(client, admin_headers):
    response = await _create(client, UNITS, admin_headers, name_ja="名前だけ")
    assert response.status_code == 422
    assert response.json() == {"detail": "field_required"}


async def test_the_same_unit_twice_is_refused(client, admin_headers):
    await _create(client, UNITS, admin_headers, name_en="School of Testing")
    again = await _create(client, UNITS, admin_headers, name_en="School of Testing")
    assert again.status_code == 409
    assert again.json() == {"detail": "value_in_use"}


async def test_fields_save_one_at_a_time_with_conflicts(client, admin_headers):
    unit = (await _create(client, UNITS, admin_headers, name_en="School of Testing")).json()
    url = f"{UNITS}/{unit['id']}"
    assert (await _patch(client, url, admin_headers, "name_ja", "一")).json()["version"] == 1
    stale = await _patch(client, url, admin_headers, "name_ja", "二", 0)
    assert stale.status_code == 409
    assert stale.json()["current_value"] == "一"
    assert (await _patch(client, url, admin_headers, "key", "x")).status_code == 422


async def test_a_reference_must_exist_in_this_institution(client, admin_headers):
    async with SessionLocal() as db:
        other = Institution(name_en="Other University", timezone="UTC", settings={})
        db.add(other)
        await db.flush()
        foreign = ResearchField(institution_id=other.id, name_en="Elsewhere")
        db.add(foreign)
        await db.commit()
    unit = (await _create(client, UNITS, admin_headers, name_en="School of Testing")).json()
    response = await _patch(
        client, f"{UNITS}/{unit['id']}", admin_headers, "default_field_id", str(foreign.id)
    )
    assert response.status_code == 422
    assert response.json() == {"detail": "unknown_reference"}


async def test_retiring_keeps_the_entry(client, admin_headers):
    unit = (await _create(client, UNITS, admin_headers, name_en="Old School")).json()
    await _patch(client, f"{UNITS}/{unit['id']}", admin_headers, "is_active", False)
    rows = (await client.get(UNITS, headers=admin_headers)).json()
    assert [(row["name_en"], row["is_active"]) for row in rows] == [("Old School", False)]


async def test_there_is_no_way_to_delete_an_entry(client, admin_headers):
    unit = (await _create(client, UNITS, admin_headers, name_en="Stays")).json()
    response = await client.delete(f"{UNITS}/{unit['id']}", headers=admin_headers)
    assert response.status_code == 405


async def test_list_changes_are_audited_with_the_admin(client, admin_headers):
    unit = (await _create(client, UNITS, admin_headers, name_en="School of Testing")).json()
    await _patch(client, f"{UNITS}/{unit['id']}", admin_headers, "name_ja", "試験")
    async with SessionLocal() as db:
        chief = await db.scalar(select(User.id).where(User.email == "chief@example.org"))
        entries = list(await db.scalars(select(AuditLog).where(AuditLog.entity_id == unit["id"])))
    assert {entry.action for entry in entries} == {"create", "update"}
    assert {entry.user_id for entry in entries} == {chief}


# ---------------------------------------------------------------- writers


async def test_a_writer_links_to_at_most_one_user(client, admin_headers, make_user):
    user = await make_user()
    one = (await _create(client, WRITERS, admin_headers, display_name_en="A. Writer")).json()
    two = (await _create(client, WRITERS, admin_headers, display_name_en="B. Writer")).json()
    linked = await _patch(client, f"{WRITERS}/{one['id']}", admin_headers, "user_id", str(user.id))
    assert linked.status_code == 200
    again = await _patch(client, f"{WRITERS}/{two['id']}", admin_headers, "user_id", str(user.id))
    assert again.status_code == 409
    assert again.json() == {"detail": "value_in_use"}


# ---------------------------------------------------------------- vocabularies


async def test_a_vocabulary_and_its_items(client, admin_headers):
    vocabulary = (await _create(client, VOCABULARIES, admin_headers, name_en="Press Types")).json()
    assert vocabulary["key"] == "press_types"
    url = f"{VOCABULARIES}/{vocabulary['id']}/items"

    first = await _create(client, url, admin_headers, label_en="Wire Service", label_ja="通信社")
    second = await _create(client, url, admin_headers, label_en="Wire service")
    assert first.status_code == 201
    assert first.json()["key"] == "wire_service"
    # The same label gets its own key.
    assert second.json()["key"] == "wire_service_2"
    rows = (await client.get(url, headers=admin_headers)).json()
    assert [row["position"] for row in rows] == [0, 1]

    patched = await _patch(
        client,
        f"/api/v1/lists/vocabulary-items/{first.json()['id']}",
        admin_headers,
        "is_active",
        False,
    )
    assert patched.json()["value"] is False


async def test_items_of_an_unknown_vocabulary_are_not_found(client, admin_headers):
    url = f"{VOCABULARIES}/00000000-0000-0000-0000-000000000000/items"
    assert (await client.get(url, headers=admin_headers)).status_code == 404


async def test_item_csv_round_trip(client, admin_headers):
    vocabulary = (await _create(client, VOCABULARIES, admin_headers, name_en="Press Types")).json()
    url = f"{VOCABULARIES}/{vocabulary['id']}/items"
    report = await _import(
        client,
        f"{url}/import",
        admin_headers,
        'key,label_en,label_ja,aliases,active\nwire,Wire,通信社,"W, X",Y\n',
    )
    assert report.json()["created"] == 1
    exported = (await client.get(f"{url}/export", headers=admin_headers)).content.decode("utf-8")
    assert "通信社" in exported
    again = await _import(client, f"{url}/import", admin_headers, exported)
    assert (again.json()["created"], again.json()["unchanged"]) == (0, 1)


# ---------------------------------------------------------------- CSV export


async def test_export_is_excel_friendly_and_keeps_japanese(client, admin_headers):
    await _create(client, UNITS, admin_headers, name_en="School of Testing", name_ja="試験研究科")
    response = await client.get(f"{UNITS}/export", headers=admin_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert 'filename="units.csv"' in response.headers["content-disposition"]
    assert response.content.startswith(b"\xef\xbb\xbf")
    text = response.content.decode("utf-8-sig")
    assert text.splitlines()[0] == (
        "key,name_en,name_ja,short_label,type,aliases,default_field,active"
    )
    assert "試験研究科" in text


async def test_a_cell_that_looks_like_a_formula_is_exported_as_text(client, admin_headers):
    await _create(client, UNITS, admin_headers, name_en="=SUM(A1:A9)")
    text = (await client.get(f"{UNITS}/export", headers=admin_headers)).content.decode("utf-8-sig")
    assert ",'=SUM(A1:A9)," in text
    # And comes back as it was.
    report = (await _import(client, f"{UNITS}/import", admin_headers, text)).json()
    assert report["unchanged"] == 1
    assert report["errors"] == []


async def test_the_vocabulary_list_itself_has_no_csv(client, admin_headers):
    assert (await client.get(f"{VOCABULARIES}/export", headers=admin_headers)).status_code == 404


# ---------------------------------------------------------------- CSV import


UNITS_CSV = (
    "key,name_en,name_ja,short_label,type,aliases,default_field,active\n"
    'ONE,School One,第一研究科,One,school,"A, B",Sciences,Y\n'
    "TWO,School Two,,,,,,N\n"
)


async def test_a_dry_run_reports_what_would_happen_and_changes_nothing(client, admin_headers):
    await _create(client, FIELDS, admin_headers, name_en="Sciences")
    report = (await _import(client, f"{UNITS}/import", admin_headers, UNITS_CSV, True)).json()
    assert report == {"created": 2, "updated": 0, "unchanged": 0, "errors": [], "dry_run": True}
    assert (await client.get(UNITS, headers=admin_headers)).json() == []


async def test_import_creates_then_updates_by_key(client, admin_headers):
    field = (await _create(client, FIELDS, admin_headers, name_en="Sciences")).json()
    first = (await _import(client, f"{UNITS}/import", admin_headers, UNITS_CSV)).json()
    assert (first["created"], first["updated"]) == (2, 0)
    rows = {row["key"]: row for row in (await client.get(UNITS, headers=admin_headers)).json()}
    assert rows["ONE"]["aliases"] == ["A", "B"]
    assert rows["ONE"]["default_field_id"] == field["id"]
    assert rows["TWO"]["is_active"] is False

    changed = UNITS_CSV.replace("第一研究科", "第壱研究科")
    second = (await _import(client, f"{UNITS}/import", admin_headers, changed)).json()
    assert (second["created"], second["updated"], second["unchanged"]) == (0, 1, 1)
    rows = {row["key"]: row for row in (await client.get(UNITS, headers=admin_headers)).json()}
    assert rows["ONE"]["name_ja"] == "第壱研究科"
    # A save from someone with an older screen is then a conflict, not an overwrite.
    assert rows["ONE"]["field_versions"]["name_ja"] == 1


async def test_rows_that_cannot_be_used_are_reported_and_the_rest_still_apply(
    client, admin_headers
):
    text = (
        "key,name_en,type,default_field,active\n"
        "GOOD,School Good,school,,Y\n"
        ",No Key,school,,Y\n"
        "BADTYPE,School,club,,Y\n"
        "BADFIELD,School,school,Nowhere,Y\n"
        "BADFLAG,School,school,,perhaps\n"
    )
    report = (await _import(client, f"{UNITS}/import", admin_headers, text)).json()
    assert report["created"] == 1
    assert report["errors"] == [
        {"row": 3, "key": "", "code": "field_required"},
        {"row": 4, "key": "BADTYPE", "code": "field_invalid"},
        {"row": 5, "key": "BADFIELD", "code": "unknown_reference"},
        {"row": 6, "key": "BADFLAG", "code": "field_invalid"},
    ]


async def test_a_file_without_the_key_column_is_refused(client, admin_headers):
    response = await _import(client, f"{UNITS}/import", admin_headers, "name_en\nSomething\n")
    assert response.status_code == 422
    assert response.json() == {"detail": "csv_missing_column"}


async def test_exporting_then_importing_changes_nothing(client, admin_headers):
    await _create(client, FIELDS, admin_headers, name_en="Sciences", name_ja="理系")
    await _import(client, f"{UNITS}/import", admin_headers, UNITS_CSV)
    for url in (UNITS, FIELDS):
        text = (await client.get(f"{url}/export", headers=admin_headers)).content.decode("utf-8")
        report = (await _import(client, f"{url}/import", admin_headers, text)).json()
        assert report["created"] == report["updated"] == 0
        assert report["errors"] == []


async def test_writers_import_links_a_user_by_email(client, admin_headers, make_user):
    user = await make_user("someone@example.org")
    text = (
        "display_name_en,display_name_ja,full_name,user_email,active\n"
        "A. Writer,,Anna Writer,someone@example.org,Y\n"
        "B. Writer,,,nobody@example.org,Y\n"
    )
    report = (await _import(client, f"{WRITERS}/import", admin_headers, text)).json()
    assert report["created"] == 1
    assert report["errors"] == [{"row": 3, "key": "B. Writer", "code": "unknown_reference"}]
    async with SessionLocal() as db:
        writer = await db.scalar(select(Writer))
    assert writer.user_id == user.id
    exported = (await client.get(f"{WRITERS}/export", headers=admin_headers)).content.decode(
        "utf-8-sig"
    )
    assert "someone@example.org" in exported


async def test_a_clash_costs_that_row_and_not_the_file(client, admin_headers, make_user):
    await make_user("someone@example.org")
    text = (
        "display_name_en,user_email\n"
        "A. Writer,someone@example.org\n"
        "B. Writer,someone@example.org\n"
        "C. Writer,\n"
    )
    report = (await _import(client, f"{WRITERS}/import", admin_headers, text)).json()
    assert report["created"] == 2
    assert report["errors"] == [{"row": 3, "key": "B. Writer", "code": "value_in_use"}]
    rows = (await client.get(WRITERS, headers=admin_headers)).json()
    assert sorted(row["display_name_en"] for row in rows) == ["A. Writer", "C. Writer"]


@pytest.mark.parametrize("dry_run", [True, False])
async def test_import_reports_whether_it_was_a_dry_run(client, admin_headers, dry_run):
    report = await _import(
        client, f"{FIELDS}/import", admin_headers, "name_en\nSciences\n", dry_run
    )
    assert report.json()["dry_run"] is dry_run


async def test_imported_rows_are_audited_with_the_admin(client, admin_headers):
    await _import(client, f"{FIELDS}/import", admin_headers, "name_en\nSciences\n")
    async with SessionLocal() as db:
        chief = await db.scalar(select(User.id).where(User.email == "chief@example.org"))
        entry = await db.scalar(select(AuditLog).where(AuditLog.entity_type == "research_fields"))
    assert entry.user_id == chief


async def test_a_dry_run_leaves_no_audit_entries(client, admin_headers):
    await _import(client, f"{FIELDS}/import", admin_headers, "name_en\nSciences\n", True)
    async with SessionLocal() as db:
        entry = await db.scalar(select(AuditLog).where(AuditLog.entity_type == "research_fields"))
    assert entry is None
