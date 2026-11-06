"""The researcher directory. Names here are synthetic."""

from sqlalchemy import select

from app.database import SessionLocal
from app.models import AuditLog, Institution, Release, Researcher, UserRole

URL = "/api/v1/researchers"


async def _create(client, headers, name="Test Person", **values):
    response = await client.post(URL, headers=headers, json={"name": name, **values})
    assert response.status_code == 201, response.text
    return response.json()


async def _patch(client, researcher_id, headers, field, value, version=0):
    return await client.patch(
        f"{URL}/{researcher_id}",
        headers=headers,
        json={"field": field, "value": value, "version": version},
    )


async def _names(client, headers, **params) -> list[str]:
    response = await client.get(URL, headers=headers, params=params)
    assert response.status_code == 200
    return [row["name"] for row in response.json()["items"]]


async def _release_for(researcher_id: str) -> Release:
    async with SessionLocal() as db:
        institution_id = await db.scalar(select(Institution.id))
        release = Release(
            institution_id=institution_id, title="A release", researcher_id=researcher_id
        )
        db.add(release)
        await db.commit()
        return release


async def test_viewers_read_editors_and_admins_change(client, headers_for):
    admin = await headers_for(UserRole.admin)
    editor = await headers_for(UserRole.editor)
    viewer = await headers_for(UserRole.viewer)
    made = await _create(client, editor)
    await _create(client, admin, name="Another Person")

    assert len(await _names(client, viewer)) == 2
    denied = await client.post(URL, headers=viewer, json={"name": "No"})
    assert denied.status_code == 403
    assert (await _patch(client, made["id"], viewer, "name", "No")).status_code == 403
    merged = await client.post(f"{URL}/{made['id']}/merge", headers=viewer, json={"into_id": "x"})
    assert merged.status_code in (403, 422)


async def test_a_new_researcher_starts_incomplete_with_no_gender_recorded(client, admin_headers):
    made = await _create(client, admin_headers)
    assert made["status"] == "incomplete"
    assert made["gender"] == "not_recorded"
    assert made["release_count"] == 0


async def test_identical_names_are_two_people(client, admin_headers):
    """R6.3.1."""
    one = await _create(client, admin_headers)
    two = await _create(client, admin_headers)
    assert one["id"] != two["id"]


async def test_a_name_is_required_and_values_come_from_their_lists(client, admin_headers):
    blank = await client.post(URL, headers=admin_headers, json={"name": "  "})
    assert (blank.status_code, blank.json()) == (422, {"detail": "field_required"})
    made = await _create(client, admin_headers)
    bad = await _patch(client, made["id"], admin_headers, "gender", "unknown")
    assert (bad.status_code, bad.json()) == (422, {"detail": "field_invalid"})
    bad = await _patch(client, made["id"], admin_headers, "status", "maybe")
    assert bad.status_code == 422


async def test_saving_one_field_with_conflict_detection(client, admin_headers):
    made = await _create(client, admin_headers)
    saved = await _patch(client, made["id"], admin_headers, "given_name", "Test")
    assert saved.json()["version"] == 1
    stale = await _patch(client, made["id"], admin_headers, "given_name", "Other", 0)
    assert stale.status_code == 409
    assert stale.json()["current_value"] == "Test"


async def test_search_covers_names_and_identifiers(client, admin_headers):
    await _create(client, admin_headers, name="Alice Example", name_ja="例 アリス")
    made = await _create(client, admin_headers, name="Bob Sample", given_name="Robert")
    await _patch(client, made["id"], admin_headers, "orcid", "0000-0001-2345-6789")

    assert await _names(client, admin_headers, search="ALICE") == ["Alice Example"]
    assert await _names(client, admin_headers, search="アリス") == ["Alice Example"]
    assert await _names(client, admin_headers, search="robert") == ["Bob Sample"]
    assert await _names(client, admin_headers, search="2345") == ["Bob Sample"]
    assert await _names(client, admin_headers, search="nothing") == []


async def test_search_treats_wildcards_as_plain_text(client, admin_headers):
    await _create(client, admin_headers, name="Alice Example")
    assert await _names(client, admin_headers, search="%") == []
    assert await _names(client, admin_headers, search="A_ice") == []


async def test_status_filter(client, admin_headers):
    await _create(client, admin_headers, name="Done", status="verified")
    await _create(client, admin_headers, name="Open")
    assert await _names(client, admin_headers, status="verified") == ["Done"]
    assert await _names(client, admin_headers, status="incomplete") == ["Open"]


async def test_paging_and_order(client, admin_headers):
    for name in ("charlie", "Alice", "bob"):
        await _create(client, admin_headers, name=name)
    page = (await client.get(URL, headers=admin_headers, params={"limit": 2})).json()
    assert page["total"] == 3
    assert [row["name"] for row in page["items"]] == ["Alice", "bob"]
    rest = (await client.get(URL, headers=admin_headers, params={"limit": 2, "offset": 2})).json()
    assert [row["name"] for row in rest["items"]] == ["charlie"]


async def test_the_directory_counts_releases(client, admin_headers):
    made = await _create(client, admin_headers)
    await _release_for(made["id"])
    await _release_for(made["id"])
    rows = (await client.get(URL, headers=admin_headers)).json()["items"]
    assert rows[0]["release_count"] == 2


# ---------------------------------------------------------------- merging


async def test_merging_moves_releases_and_hides_the_old_record(client, admin_headers):
    """R6.3.2."""
    old = await _create(client, admin_headers, name="T. Person")
    survivor = await _create(client, admin_headers, name="Test Person")
    release = await _release_for(old["id"])
    await _release_for(survivor["id"])

    response = await client.post(
        f"{URL}/{old['id']}/merge", headers=admin_headers, json={"into_id": survivor["id"]}
    )
    assert response.status_code == 200
    assert response.json()["release_count"] == 2
    assert await _names(client, admin_headers) == ["Test Person"]

    async with SessionLocal() as db:
        assert (await db.get(Release, release.id)).researcher_id.hex == survivor["id"].replace(
            "-", ""
        )
        kept = await db.get(Researcher, old["id"])
    assert str(kept.merged_into_id) == survivor["id"]


async def test_a_merge_is_audit_logged_including_each_moved_release(client, admin_headers):
    old = await _create(client, admin_headers, name="T. Person")
    survivor = await _create(client, admin_headers, name="Test Person")
    release = await _release_for(old["id"])
    await client.post(
        f"{URL}/{old['id']}/merge", headers=admin_headers, json={"into_id": survivor["id"]}
    )
    async with SessionLocal() as db:
        moved = await db.scalar(
            select(AuditLog).where(
                AuditLog.entity_id == release.id, AuditLog.field == "researcher_id"
            )
        )
        pointer = await db.scalar(
            select(AuditLog).where(
                AuditLog.entity_id == old["id"], AuditLog.field == "merged_into_id"
            )
        )
    assert moved.old_value == old["id"]
    assert moved.new_value == survivor["id"]
    assert moved.user_id is not None
    assert pointer.new_value == survivor["id"]


async def test_a_merge_fills_gaps_on_the_survivor_but_never_overwrites(client, admin_headers):
    old = await _create(
        client, admin_headers, name="T. Person", given_name="Old", family_name="Person"
    )
    await _patch(client, old["id"], admin_headers, "orcid", "0000-0001-2345-6789")
    await _patch(client, old["id"], admin_headers, "gender", "F")
    survivor = await _create(client, admin_headers, name="Test Person", given_name="Kept")

    merged = (
        await client.post(
            f"{URL}/{old['id']}/merge", headers=admin_headers, json={"into_id": survivor["id"]}
        )
    ).json()
    assert merged["name"] == "Test Person"
    assert merged["given_name"] == "Kept"
    assert merged["family_name"] == "Person"
    assert merged["orcid"] == "0000-0001-2345-6789"
    assert merged["gender"] == "F"
    # A filled gap counts as a change, so a stale screen is told about it.
    assert merged["field_versions"]["family_name"] == 1


async def test_a_recorded_gender_is_not_overwritten_by_a_merge(client, admin_headers):
    old = await _create(client, admin_headers, name="T. Person", gender="F")
    survivor = await _create(client, admin_headers, name="Test Person", gender="M")
    merged = await client.post(
        f"{URL}/{old['id']}/merge", headers=admin_headers, json={"into_id": survivor["id"]}
    )
    assert merged.json()["gender"] == "M"


async def test_earlier_merges_follow_along(client, admin_headers):
    first = await _create(client, admin_headers, name="First")
    second = await _create(client, admin_headers, name="Second")
    third = await _create(client, admin_headers, name="Third")
    await client.post(
        f"{URL}/{first['id']}/merge", headers=admin_headers, json={"into_id": second["id"]}
    )
    await client.post(
        f"{URL}/{second['id']}/merge", headers=admin_headers, json={"into_id": third["id"]}
    )
    async with SessionLocal() as db:
        assert str((await db.get(Researcher, first["id"])).merged_into_id) == third["id"]


async def test_merging_into_itself_or_a_merged_record_is_refused(client, admin_headers):
    old = await _create(client, admin_headers, name="Old")
    survivor = await _create(client, admin_headers, name="Survivor")
    other = await _create(client, admin_headers, name="Other")

    itself = await client.post(
        f"{URL}/{old['id']}/merge", headers=admin_headers, json={"into_id": old["id"]}
    )
    assert (itself.status_code, itself.json()) == (422, {"detail": "merge_into_self"})

    await client.post(
        f"{URL}/{old['id']}/merge", headers=admin_headers, json={"into_id": survivor["id"]}
    )
    for source, target in ((old, other), (other, old)):
        again = await client.post(
            f"{URL}/{source['id']}/merge", headers=admin_headers, json={"into_id": target["id"]}
        )
        assert (again.status_code, again.json()) == (409, {"detail": "researcher_merged"})
    edit = await _patch(client, old["id"], admin_headers, "name", "Changed")
    assert (edit.status_code, edit.json()) == (409, {"detail": "researcher_merged"})


async def test_records_of_another_institution_are_out_of_reach(client, admin_headers):
    async with SessionLocal() as db:
        other = Institution(name_en="Other University", timezone="UTC", settings={})
        db.add(other)
        await db.flush()
        foreign = Researcher(institution_id=other.id, name="Elsewhere")
        db.add(foreign)
        await db.commit()
    mine = await _create(client, admin_headers)
    assert await _names(client, admin_headers) == ["Test Person"]
    assert (await _patch(client, foreign.id, admin_headers, "name", "No")).status_code == 404
    merge = await client.post(
        f"{URL}/{mine['id']}/merge", headers=admin_headers, json={"into_id": str(foreign.id)}
    )
    assert merge.status_code == 404
