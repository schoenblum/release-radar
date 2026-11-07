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


# ---------------------------------------------------------------- undoing a merge


async def _merge(client, headers, source, target):
    response = await client.post(
        f"{URL}/{source['id']}/merge", headers=headers, json={"into_id": target["id"]}
    )
    assert response.status_code == 200, response.text
    return response.json()


async def _unmerge(client, headers, source):
    return await client.post(f"{URL}/{source['id']}/unmerge", headers=headers)


async def _researcher_of(release: Release) -> str:
    async with SessionLocal() as db:
        return str((await db.get(Release, release.id)).researcher_id)


async def test_a_merge_made_in_error_can_be_undone(client, admin_headers):
    """R6.3.2."""
    old = await _create(client, admin_headers, name="Same Name")
    survivor = await _create(client, admin_headers, name="Same Name")
    theirs = await _release_for(old["id"])
    kept = await _release_for(survivor["id"])
    await _merge(client, admin_headers, old, survivor)
    assert await _names(client, admin_headers) == ["Same Name"]

    response = await _unmerge(client, admin_headers, old)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["restored"]["id"] == old["id"]
    assert body["restored"]["merged_into_id"] is None
    assert body["restored"]["release_count"] == 1
    assert body["survivor"]["release_count"] == 1
    assert await _researcher_of(theirs) == old["id"]
    assert await _researcher_of(kept) == survivor["id"]
    assert await _names(client, admin_headers) == ["Same Name", "Same Name"]


async def test_undoing_takes_back_what_the_merge_filled_in(client, admin_headers):
    old = await _create(client, admin_headers, name="Old", family_name="Person", gender="F")
    await _patch(client, old["id"], admin_headers, "orcid", "0000-0001-2345-6789")
    survivor = await _create(client, admin_headers, name="Survivor", given_name="Kept")
    merged = await _merge(client, admin_headers, old, survivor)
    assert (merged["family_name"], merged["orcid"], merged["gender"]) == (
        "Person",
        "0000-0001-2345-6789",
        "F",
    )

    back = (await _unmerge(client, admin_headers, old)).json()["survivor"]
    assert (back["family_name"], back["orcid"], back["gender"]) == (None, None, "not_recorded")
    assert back["given_name"] == "Kept"
    # The restored record has its own details again.
    restored = (await client.get(f"{URL}/{old['id']}", headers=admin_headers)).json()
    assert (restored["family_name"], restored["orcid"]) == ("Person", "0000-0001-2345-6789")


async def test_undoing_leaves_what_someone_changed_since(client, admin_headers):
    old = await _create(client, admin_headers, name="Old", family_name="Person")
    survivor = await _create(client, admin_headers, name="Survivor")
    moved = await _release_for(old["id"])
    merged = await _merge(client, admin_headers, old, survivor)
    await _patch(client, survivor["id"], admin_headers, "family_name", "Changed", 1)
    other = await _create(client, admin_headers, name="Other")
    # The release has since moved on by itself.
    await client.post(
        f"{URL}/{merged['id']}/split",
        headers=admin_headers,
        json={"release_ids": [str(moved.id)], "into_id": other["id"]},
    )

    back = (await _unmerge(client, admin_headers, old)).json()
    assert back["survivor"]["family_name"] == "Changed"
    assert back["restored"]["release_count"] == 0
    assert await _researcher_of(moved) == other["id"]


async def test_undoing_works_after_the_survivor_was_merged_again(client, admin_headers):
    first = await _create(client, admin_headers, name="First")
    second = await _create(client, admin_headers, name="Second")
    third = await _create(client, admin_headers, name="Third")
    of_first = await _release_for(first["id"])
    of_second = await _release_for(second["id"])
    await _merge(client, admin_headers, first, second)
    await _merge(client, admin_headers, second, third)

    assert (await _unmerge(client, admin_headers, first)).status_code == 200
    assert await _researcher_of(of_first) == first["id"]
    assert await _researcher_of(of_second) == third["id"]
    assert (await _unmerge(client, admin_headers, second)).status_code == 200
    assert await _researcher_of(of_second) == second["id"]


async def test_only_a_merged_record_can_be_unmerged(client, admin_headers):
    live = await _create(client, admin_headers)
    response = await _unmerge(client, admin_headers, live)
    assert (response.status_code, response.json()) == (409, {"detail": "researcher_not_merged"})


async def test_a_viewer_cannot_undo_a_merge_or_split(client, headers_for):
    editor = await headers_for(UserRole.editor)
    viewer = await headers_for(UserRole.viewer)
    old = await _create(client, editor)
    assert (await _unmerge(client, viewer, old)).status_code == 403
    refused = await client.post(
        f"{URL}/{old['id']}/split",
        headers=viewer,
        json={"release_ids": ["00000000-0000-0000-0000-000000000000"]},
    )
    assert refused.status_code == 403


# ---------------------------------------------------------------- splitting


async def _split(client, headers, source, releases, **body):
    return await client.post(
        f"{URL}/{source['id']}/split",
        headers=headers,
        json={"release_ids": [str(release.id) for release in releases], **body},
    )


async def test_splitting_moves_releases_to_a_new_record_of_the_same_name(client, admin_headers):
    """R6.3.2: one record covering two people."""
    source = await _create(
        client,
        admin_headers,
        name="Same Name",
        given_name="Same",
        family_name="Name",
        gender="F",
        status="verified",
    )
    stays = await _release_for(source["id"])
    moves = await _release_for(source["id"])

    response = await _split(client, admin_headers, source, [moves])
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["created"] is True
    target = body["target"]
    assert target["id"] != source["id"]
    assert (target["name"], target["given_name"], target["family_name"]) == (
        "Same Name",
        "Same",
        "Name",
    )
    # They may not be the same person, so nothing personal is assumed, and it is flagged.
    assert (target["gender"], target["status"]) == ("not_recorded", "incomplete")
    assert (body["source"]["release_count"], target["release_count"]) == (1, 1)
    assert (body["source"]["same_name_count"], target["same_name_count"]) == (1, 1)
    assert await _researcher_of(stays) == source["id"]
    assert await _researcher_of(moves) == target["id"]


async def test_a_split_can_name_the_new_record_and_how_to_tell_it_apart(client, admin_headers):
    source = await _create(client, admin_headers, name="Same Name", given_name="Same")
    moves = await _release_for(source["id"])
    body = (
        await _split(
            client, admin_headers, source, [moves], name="Other Name", notes="Marine biology"
        )
    ).json()
    target = body["target"]
    assert (target["name"], target["given_name"], target["notes"]) == (
        "Other Name",
        None,
        "Marine biology",
    )
    assert target["same_name_count"] == 0


async def test_a_split_can_move_releases_to_an_existing_record(client, admin_headers):
    source = await _create(client, admin_headers, name="One")
    target = await _create(client, admin_headers, name="Two")
    moves = await _release_for(source["id"])
    body = (await _split(client, admin_headers, source, [moves], into_id=target["id"])).json()
    assert body["created"] is False
    assert body["target"]["id"] == target["id"]
    assert body["target"]["release_count"] == 1


async def test_a_split_is_audit_logged_for_each_release(client, admin_headers):
    source = await _create(client, admin_headers)
    moves = await _release_for(source["id"])
    target = (await _split(client, admin_headers, source, [moves])).json()["target"]
    async with SessionLocal() as db:
        entry = await db.scalar(
            select(AuditLog).where(
                AuditLog.entity_id == moves.id, AuditLog.field == "researcher_id"
            )
        )
    assert (entry.old_value, entry.new_value) == (source["id"], target["id"])
    assert entry.user_id is not None


async def test_a_split_only_moves_what_is_on_the_record(client, admin_headers):
    source = await _create(client, admin_headers, name="One")
    other = await _create(client, admin_headers, name="Two")
    elsewhere = await _release_for(other["id"])
    response = await _split(client, admin_headers, source, [elsewhere])
    assert (response.status_code, response.json()) == (409, {"detail": "release_moved"})
    assert await _researcher_of(elsewhere) == other["id"]
    assert await _names(client, admin_headers) == ["One", "Two"]


async def test_a_split_needs_a_release_and_a_real_target(client, admin_headers):
    source = await _create(client, admin_headers)
    moves = await _release_for(source["id"])
    empty = await client.post(
        f"{URL}/{source['id']}/split", headers=admin_headers, json={"release_ids": []}
    )
    assert empty.status_code == 422
    itself = await _split(client, admin_headers, source, [moves], into_id=source["id"])
    assert (itself.status_code, itself.json()) == (422, {"detail": "split_into_self"})
    gone = await _split(
        client, admin_headers, source, [moves], into_id="00000000-0000-0000-0000-000000000000"
    )
    assert gone.status_code == 404
    other = await _create(client, admin_headers, name="Other")
    third = await _create(client, admin_headers, name="Third")
    await _merge(client, admin_headers, other, third)
    merged = await _split(client, admin_headers, source, [moves], into_id=other["id"])
    assert (merged.status_code, merged.json()) == (409, {"detail": "researcher_merged"})
    merged = await _split(client, admin_headers, other, [moves])
    assert (merged.status_code, merged.json()) == (409, {"detail": "researcher_merged"})


async def test_a_split_stays_within_the_institution(client, admin_headers):
    async with SessionLocal() as db:
        other = Institution(name_en="Other University", timezone="UTC", settings={})
        db.add(other)
        await db.flush()
        foreign = Researcher(institution_id=other.id, name="Elsewhere")
        db.add(foreign)
        await db.commit()
    mine = await _create(client, admin_headers)
    moves = await _release_for(mine["id"])
    response = await _split(client, admin_headers, mine, [moves], into_id=str(foreign.id))
    assert response.status_code == 404
    response = await client.get(f"{URL}/{foreign.id}", headers=admin_headers)
    assert response.status_code == 404


# ---------------------------------------------------------------- telling people apart


async def test_records_show_how_many_others_share_their_name(client, admin_headers):
    await _create(client, admin_headers, name="Same Name")
    await _create(client, admin_headers, name="  same   NAME ")
    await _create(client, admin_headers, name="Other Name")
    rows = (await client.get(URL, headers=admin_headers)).json()["items"]
    assert {row["name"]: row["same_name_count"] for row in rows} == {
        "Same Name": 1,
        "same   NAME": 1,
        "Other Name": 0,
    }


async def test_same_name_finds_the_records_to_look_at(client, admin_headers):
    await _create(client, admin_headers, name="Same Name")
    await _create(client, admin_headers, name="Same Name")
    await _create(client, admin_headers, name="Other Name")
    found = (await client.get(URL, headers=admin_headers, params={"same_name": True})).json()
    assert [row["name"] for row in found["items"]] == ["Same Name", "Same Name"]
    assert found["total"] == 2


async def test_a_merged_record_no_longer_counts_as_a_namesake(client, admin_headers):
    one = await _create(client, admin_headers, name="Same Name")
    two = await _create(client, admin_headers, name="Same Name")
    merged = await _merge(client, admin_headers, one, two)
    assert merged["same_name_count"] == 0
    assert merged["merged_count"] == 1


async def test_notes_can_tell_two_people_apart_and_be_searched(client, admin_headers):
    made = await _create(client, admin_headers, name="Same Name")
    await _patch(client, made["id"], admin_headers, "notes", "Marine biology, north campus")
    rows = (await client.get(URL, headers=admin_headers, params={"search": "marine"})).json()
    assert [row["notes"] for row in rows["items"]] == ["Marine biology, north campus"]


async def test_a_record_lists_its_releases_and_what_was_merged_into_it(client, admin_headers):
    survivor = await _create(client, admin_headers, name="Survivor")
    old = await _create(client, admin_headers, name="Old")
    await _release_for(old["id"])
    await _release_for(survivor["id"])
    await _merge(client, admin_headers, old, survivor)

    detail = (await client.get(f"{URL}/{survivor['id']}", headers=admin_headers)).json()
    assert [item["title"] for item in detail["releases"]] == ["A release", "A release"]
    assert detail["release_count"] == 2
    assert [
        (item["id"], item["name"], item["release_count"]) for item in detail["merged_records"]
    ] == [(old["id"], "Old", 1)]
    missing = await client.get(f"{URL}/00000000-0000-0000-0000-000000000000", headers=admin_headers)
    assert missing.status_code == 404


async def test_a_removed_release_does_not_count_and_does_not_show(client, admin_headers):
    made = await _create(client, admin_headers)
    release = await _release_for(made["id"])
    await client.delete(f"/api/v1/releases/{release.id}", headers=admin_headers)
    rows = (await client.get(URL, headers=admin_headers)).json()["items"]
    assert rows[0]["release_count"] == 0
    detail = (await client.get(f"{URL}/{made['id']}", headers=admin_headers)).json()
    assert detail["releases"] == []


# ---------------------------------------------------------------- removing an empty record


async def test_undoing_a_split_can_leave_no_trace(client, admin_headers):
    source = await _create(client, admin_headers, name="Same Name")
    moves = await _release_for(source["id"])
    target = (await _split(client, admin_headers, source, [moves])).json()["target"]

    back = await _split(client, admin_headers, target, [moves], into_id=source["id"])
    assert back.status_code == 200
    assert (await client.delete(f"{URL}/{target['id']}", headers=admin_headers)).status_code == 204

    assert await _names(client, admin_headers) == ["Same Name"]
    assert await _researcher_of(moves) == source["id"]
    detail = (await client.get(f"{URL}/{source['id']}", headers=admin_headers)).json()
    assert detail["merged_records"] == []
    # The history of a record outlives the record.
    async with SessionLocal() as db:
        entry = await db.scalar(
            select(AuditLog).where(AuditLog.entity_id == target["id"], AuditLog.action == "delete")
        )
    assert entry.old_value["name"] == "Same Name"
    assert entry.user_id is not None


async def test_only_a_record_nothing_refers_to_can_be_removed(client, admin_headers):
    with_release = await _create(client, admin_headers, name="Has a release")
    release = await _release_for(with_release["id"])
    response = await client.delete(f"{URL}/{with_release['id']}", headers=admin_headers)
    assert (response.status_code, response.json()) == (409, {"detail": "researcher_in_use"})

    # A removed release can come back, so it still counts.
    await client.delete(f"/api/v1/releases/{release.id}", headers=admin_headers)
    response = await client.delete(f"{URL}/{with_release['id']}", headers=admin_headers)
    assert response.status_code == 409

    survivor = await _create(client, admin_headers, name="Survivor")
    merged = await _create(client, admin_headers, name="Merged")
    await _merge(client, admin_headers, merged, survivor)
    for record in (survivor, merged):
        response = await client.delete(f"{URL}/{record['id']}", headers=admin_headers)
        assert (response.status_code, response.json()) == (409, {"detail": "researcher_in_use"})


async def test_a_viewer_cannot_remove_a_record(client, headers_for):
    editor = await headers_for(UserRole.editor)
    viewer = await headers_for(UserRole.viewer)
    made = await _create(client, editor)
    assert (await client.delete(f"{URL}/{made['id']}", headers=viewer)).status_code == 403
    assert (await client.delete(f"{URL}/{made['id']}", headers=editor)).status_code == 204
    gone = await client.delete(f"{URL}/{made['id']}", headers=editor)
    assert gone.status_code == 404
