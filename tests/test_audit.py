"""The audit log: every change, with who and when, and never a secret (R3.4.4)."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import delete, select

from app.database import SessionLocal
from app.models import AuditLog, Institution, Reading, Release, Researcher, User, UserRole
from app.services.audit import REDACTED, set_actor
from tests.conftest import bearer, plain_body, sign_in

PASSWORD = "correct-horse-battery"


async def _institution_id():
    async with SessionLocal() as db:
        return await db.scalar(select(Institution.id))


async def _entries(entity_id, action: str | None = None) -> list[AuditLog]:
    async with SessionLocal() as db:
        query = select(AuditLog).where(AuditLog.entity_id == entity_id)
        if action:
            query = query.where(AuditLog.action == action)
        return list(await db.scalars(query))


async def _create_release(**values) -> Release:
    async with SessionLocal() as db:
        release = Release(institution_id=await _institution_id(), title="A title", **values)
        db.add(release)
        await db.commit()
        return release


async def test_creating_a_record_logs_a_snapshot_without_technical_columns():
    release = await _create_release(doi="10.1234/example", release_date=date(2026, 4, 1))
    entries = await _entries(release.id)
    assert [entry.action for entry in entries] == ["create"]
    snapshot = entries[0].new_value
    assert snapshot["title"] == "A title"
    assert snapshot["doi"] == "10.1234/example"
    assert snapshot["release_date"] == "2026-04-01"
    assert "id" not in snapshot
    assert "field_versions" not in snapshot
    assert entries[0].entity_type == "releases"
    assert entries[0].institution_id == release.institution_id
    assert entries[0].created_at is not None


async def test_a_change_logs_entity_field_old_new_and_user(make_user):
    user = await make_user()
    release = await _create_release()
    async with SessionLocal() as db:
        set_actor(db, user.id)
        stored = await db.get(Release, release.id)
        stored.title = "A better title"
        await db.commit()

    entry = (await _entries(release.id, "update"))[0]
    assert entry.field == "title"
    assert entry.old_value == "A title"
    assert entry.new_value == "A better title"
    assert entry.user_id == user.id


async def test_several_fields_changed_together_each_get_an_entry():
    release = await _create_release()
    async with SessionLocal() as db:
        stored = await db.get(Release, release.id)
        stored.title = "New"
        stored.notes = "Added"
        await db.commit()
    entries = {entry.field: entry for entry in await _entries(release.id, "update")}
    assert set(entries) == {"title", "notes"}
    assert entries["notes"].old_value is None
    assert entries["notes"].new_value == "Added"


async def test_saving_the_same_value_logs_nothing():
    release = await _create_release()
    async with SessionLocal() as db:
        stored = await db.get(Release, release.id)
        stored.title = "A title"
        await db.commit()
    assert await _entries(release.id, "update") == []


async def test_a_change_without_a_user_is_recorded_as_the_system():
    release = await _create_release()
    async with SessionLocal() as db:
        stored = await db.get(Release, release.id)
        stored.title = "Changed by a job"
        await db.commit()
    assert (await _entries(release.id, "update"))[0].user_id is None


async def test_a_rollback_removes_the_entry_with_the_change():
    release = await _create_release()
    async with SessionLocal() as db:
        stored = await db.get(Release, release.id)
        stored.title = "Never saved"
        await db.flush()
        await db.rollback()
    assert await _entries(release.id, "update") == []


async def test_deleting_a_record_keeps_its_history_and_a_final_snapshot():
    async with SessionLocal() as db:
        researcher = Researcher(institution_id=await _institution_id(), name="Test Person")
        db.add(researcher)
        await db.commit()
    async with SessionLocal() as db:
        await db.delete(await db.get(Researcher, researcher.id))
        await db.commit()
    entries = {entry.action: entry for entry in await _entries(researcher.id)}
    assert set(entries) == {"create", "delete"}
    assert entries["delete"].old_value["name"] == "Test Person"
    assert entries["delete"].new_value is None


async def test_custom_values_are_logged_per_field():
    release = await _create_release(custom_values={"clicks": {"state": "value", "value": 1}})
    async with SessionLocal() as db:
        stored = await db.get(Release, release.id)
        stored.custom_values = {
            "clicks": {"state": "value", "value": 2},
            "pitched": {"state": "not_applicable"},
        }
        await db.commit()
    entries = {entry.field: entry for entry in await _entries(release.id, "update")}
    assert set(entries) == {"custom_values.clicks", "custom_values.pitched"}
    assert entries["custom_values.clicks"].old_value == {"state": "value", "value": 1}
    assert entries["custom_values.clicks"].new_value == {"state": "value", "value": 2}
    assert entries["custom_values.pitched"].old_value is None


async def test_values_of_every_type_can_be_logged():
    release = await _create_release()
    async with SessionLocal() as db:
        reading = await db.scalar(select(Reading).where(Reading.release_id == release.id).limit(1))
        reading.state, reading.value, reading.source = "value", Decimal("12.50"), "manual"
        await db.commit()
    entries = {entry.field: entry for entry in await _entries(reading.id, "update")}
    assert entries["value"].new_value == 12.5
    assert entries["state"].old_value == "not_applicable"
    assert entries["state"].new_value == "value"


async def test_a_flip_made_by_a_rule_is_logged_with_the_person_whose_save_caused_it(make_user):
    user = await make_user()
    release = await _create_release()
    async with SessionLocal() as db:
        reading_ids = list(
            await db.scalars(select(Reading.id).where(Reading.release_id == release.id))
        )
    async with SessionLocal() as db:
        set_actor(db, user.id)
        stored = await db.get(Release, release.id)
        stored.doi = "10.1234/example"
        await db.commit()
    async with SessionLocal() as db:
        flips = list(
            await db.scalars(
                select(AuditLog).where(
                    AuditLog.entity_id.in_(reading_ids),
                    AuditLog.field == "state",
                )
            )
        )
    # altmetric.d0 and altmetric.d28.
    assert len(flips) == 2
    assert {(flip.old_value, flip.new_value) for flip in flips} == {("not_applicable", "missing")}
    assert {flip.user_id for flip in flips} == {user.id}


async def test_who_created_and_changed_a_record_is_filled_in_automatically(make_user):
    creator = await make_user("creator@example.org")
    editor = await make_user("editor2@example.org")
    async with SessionLocal() as db:
        set_actor(db, creator.id)
        release = Release(institution_id=await _institution_id(), title="A title")
        db.add(release)
        await db.commit()
    assert (release.created_by_id, release.updated_by_id) == (creator.id, creator.id)

    async with SessionLocal() as db:
        set_actor(db, editor.id)
        stored = await db.get(Release, release.id)
        stored.title = "Changed"
        await db.commit()
    assert (stored.created_by_id, stored.updated_by_id) == (creator.id, editor.id)

    # A save that changes nothing leaves the last editor in place.
    async with SessionLocal() as db:
        set_actor(db, creator.id)
        same = await db.get(Release, release.id)
        same.title = "Changed"
        await db.commit()
    assert same.updated_by_id == editor.id


async def test_readings_created_by_a_rule_are_stamped_with_whoever_saved_the_release(make_user):
    user = await make_user()
    async with SessionLocal() as db:
        set_actor(db, user.id)
        release = Release(institution_id=await _institution_id(), title="A title")
        db.add(release)
        await db.commit()
    async with SessionLocal() as db:
        readings = list(await db.scalars(select(Reading).where(Reading.release_id == release.id)))
    assert readings
    assert {reading.created_by_id for reading in readings} == {user.id}
    # entered_by stays empty: nobody entered anything.
    assert {reading.entered_by_id for reading in readings} == {None}


async def test_institution_changes_are_logged():
    async with SessionLocal() as db:
        institution = await db.scalar(select(Institution))
        institution.contact_email = "office@example.org"
        await db.commit()
    entries = await _entries(institution.id, "update")
    assert [(entry.field, entry.new_value) for entry in entries] == [
        ("contact_email", "office@example.org")
    ]
    assert entries[0].institution_id == institution.id


# ---------------------------------------------------------------- user accounts


async def test_a_password_change_is_recorded_but_never_the_hash(client, make_user):
    user = await make_user()
    body = await sign_in(client, "editor@example.org", PASSWORD)
    response = await client.post(
        "/api/v1/auth/change-password",
        headers=bearer(body["access_token"]),
        json={"current_password": PASSWORD, "new_password": "a-brand-new-passphrase"},
    )
    assert response.status_code == 200

    entries = await _entries(user.id, "update")
    password_entry = next(entry for entry in entries if entry.field == "password_hash")
    assert password_entry.old_value == REDACTED
    assert password_entry.new_value == REDACTED
    assert password_entry.user_id == user.id

    async with SessionLocal() as db:
        current_hash = (await db.get(User, user.id)).password_hash
        everything = list(await db.scalars(select(AuditLog)))
    text = " ".join(f"{entry.old_value} {entry.new_value}" for entry in everything)
    assert current_hash not in text
    assert "$2b$" not in text


async def test_a_new_account_snapshot_does_not_contain_the_hash(make_user):
    user = await make_user()
    snapshot = (await _entries(user.id, "create"))[0].new_value
    assert snapshot["email"] == "editor@example.org"
    assert snapshot["password_hash"] == REDACTED
    assert "token_version" not in snapshot


async def test_signing_in_is_not_a_record_change(client, make_user):
    user = await make_user()
    await sign_in(client, "editor@example.org", PASSWORD)
    await client.post("/api/v1/auth/refresh")
    assert await _entries(user.id, "update") == []
    async with SessionLocal() as db:
        assert (await db.get(User, user.id)).last_login_at is not None


async def test_an_admin_changing_a_user_is_logged_with_the_admin(client, admin_headers, make_user):
    user = await make_user()
    response = await client.patch(
        f"/api/v1/users/{user.id}", headers=admin_headers, json={"role": "viewer"}
    )
    assert response.status_code == 200
    async with SessionLocal() as db:
        chief = await db.scalar(select(User).where(User.email == "chief@example.org"))
    entries = await _entries(user.id, "update")
    assert [(e.field, e.old_value, e.new_value) for e in entries] == [("role", "editor", "viewer")]
    assert entries[0].user_id == chief.id
    async with SessionLocal() as db:
        assert (await db.get(User, user.id)).updated_by_id == chief.id


async def test_deactivating_a_user_is_logged_and_their_history_stays(
    client, admin_headers, make_user
):
    """R3.4.1: a deactivated user's name stays visible in history."""
    user = await make_user()
    await client.patch(f"/api/v1/users/{user.id}", headers=admin_headers, json={"is_active": False})
    entry = (await _entries(user.id, "update"))[0]
    assert (entry.field, entry.old_value, entry.new_value) == ("is_active", True, False)


async def test_a_new_user_records_the_admin_who_created_them(client, admin_headers):
    response = await client.post(
        "/api/v1/users", headers=admin_headers, json={"email": "new@example.org"}
    )
    new_id = response.json()["user"]["id"]
    async with SessionLocal() as db:
        chief = await db.scalar(select(User).where(User.email == "chief@example.org"))
    entry = (await _entries(new_id, "create"))[0]
    assert entry.user_id == chief.id


async def test_someone_changing_their_own_language_is_logged_as_themselves(client, make_user):
    user = await make_user()
    body = await sign_in(client, "editor@example.org", PASSWORD)
    await client.patch(
        "/api/v1/users/me", headers=bearer(body["access_token"]), json={"language": "ja"}
    )
    entry = (await _entries(user.id, "update"))[0]
    assert (entry.field, entry.new_value, entry.user_id) == ("language", "ja", user.id)


async def test_a_password_reset_is_logged_as_the_person_who_held_the_link(
    client, make_user, outbox
):
    user = await make_user()
    await client.post("/api/v1/auth/forgot-password", json={"email": "editor@example.org"})
    token = plain_body(outbox[-1][0]).split("token=")[1].split()[0]
    response = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "a-brand-new-passphrase"},
    )
    assert response.status_code == 204
    entry = next(e for e in await _entries(user.id, "update") if e.field == "password_hash")
    assert entry.user_id == user.id


async def test_a_user_with_history_cannot_be_deleted(client, admin_headers, make_user):
    """The log refers to its users with RESTRICT, so history always keeps its name (R3.4.2)."""
    async with SessionLocal() as db:
        chief = await db.scalar(select(User).where(User.email == "chief@example.org"))
    user = await make_user(role=UserRole.viewer)
    await client.patch(
        f"/api/v1/users/{user.id}", headers=admin_headers, json={"full_name": "Test Person"}
    )
    from sqlalchemy.exc import IntegrityError

    async with SessionLocal() as db:
        with pytest.raises(IntegrityError):
            await db.execute(delete(User).where(User.id == chief.id))
