"""User administration, self-service and data ownership."""

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models import AuditLog, Institution, RefreshToken, User, UserRole
from app.services.security import hash_password
from tests.conftest import bearer, plain_body, sign_in

PASSWORD = "correct-horse-battery"


@pytest.mark.parametrize("role", [UserRole.editor, UserRole.viewer])
async def test_only_admins_manage_users(client, make_user, role):
    user = await make_user("someone@example.org", PASSWORD, role)
    headers = bearer((await sign_in(client, "someone@example.org", PASSWORD))["access_token"])
    assert (await client.get("/api/v1/users", headers=headers)).status_code == 403
    created = await client.post("/api/v1/users", headers=headers, json={"email": "new@example.org"})
    assert created.status_code == 403
    changed = await client.patch(
        f"/api/v1/users/{user.id}", headers=headers, json={"role": "admin"}
    )
    assert changed.status_code == 403


async def test_create_user_sends_the_temporary_password_by_email(client, admin_headers, outbox):
    response = await client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={"email": "New@Example.org", "full_name": "Test Person", "role": "viewer"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "new@example.org"
    assert body["user"]["force_password_change"] is True
    assert body["email_sent"] is True
    # The password went to its owner, so the admin's screen does not show it.
    assert body["initial_password"] is None

    message = outbox[-1][0]
    assert message["To"] == "new@example.org"
    assert "Temporary password:" in plain_body(message)


async def test_create_user_returns_the_password_when_email_is_off(client, admin_headers):
    response = await client.post(
        "/api/v1/users", headers=admin_headers, json={"email": "new@example.org"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email_sent"] is False
    assert body["initial_password"]
    assert (await sign_in(client, "new@example.org", body["initial_password"]))["user"][
        "force_password_change"
    ] is True


async def test_create_user_records_who_did_it(client, admin_headers):
    response = await client.post(
        "/api/v1/users", headers=admin_headers, json={"email": "new@example.org"}
    )
    async with SessionLocal() as db:
        created = await db.scalar(select(User).where(User.email == "new@example.org"))
        chief = await db.scalar(select(User).where(User.email == "chief@example.org"))
    assert response.status_code == 201
    assert created.created_by_id == chief.id
    assert created.updated_by_id == chief.id


async def test_duplicate_email_is_refused(client, admin_headers, make_user):
    await make_user("taken@example.org")
    response = await client.post(
        "/api/v1/users", headers=admin_headers, json={"email": "TAKEN@example.org"}
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "email_in_use"}


async def test_admin_updates_a_user(client, admin_headers, make_user):
    user = await make_user()
    response = await client.patch(
        f"/api/v1/users/{user.id}",
        headers=admin_headers,
        json={"role": "viewer", "full_name": "New Name", "email": "Moved@example.org"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "viewer"
    assert body["full_name"] == "New Name"
    assert body["email"] == "moved@example.org"


async def test_null_does_not_erase_required_fields(client, admin_headers, make_user):
    user = await make_user()
    response = await client.patch(
        f"/api/v1/users/{user.id}",
        headers=admin_headers,
        json={"role": None, "email": None, "is_active": None},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "editor"
    assert response.json()["is_active"] is True


async def test_admin_cannot_lock_themselves_out(client, admin_headers):
    me = (await client.get("/api/v1/auth/me", headers=admin_headers)).json()
    deactivate = await client.patch(
        f"/api/v1/users/{me['id']}", headers=admin_headers, json={"is_active": False}
    )
    assert deactivate.status_code == 400
    assert deactivate.json() == {"detail": "cannot_deactivate_self"}
    demote = await client.patch(
        f"/api/v1/users/{me['id']}", headers=admin_headers, json={"role": "editor"}
    )
    assert demote.status_code == 400
    assert demote.json() == {"detail": "cannot_demote_self"}


async def test_there_is_no_way_to_delete_a_user(client, admin_headers, make_user):
    """Users are deactivated, never deleted (R3.4.1, D12)."""
    user = await make_user()
    response = await client.delete(f"/api/v1/users/{user.id}", headers=admin_headers)
    assert response.status_code == 405


async def test_database_refuses_to_delete_a_user_with_records(client, make_user):
    """Foreign keys to users use RESTRICT (R3.4.2)."""
    user = await make_user()
    await sign_in(client, "editor@example.org", PASSWORD)
    async with SessionLocal() as db:
        assert await db.scalar(select(RefreshToken.id).where(RefreshToken.user_id == user.id))
        with pytest.raises(IntegrityError):
            await db.execute(delete(User).where(User.id == user.id))


async def test_admin_resets_someones_password(client, admin_headers, make_user):
    user = await make_user()
    signed_in = await sign_in(client, "editor@example.org", PASSWORD)
    response = await client.post(f"/api/v1/users/{user.id}/reset-password", headers=admin_headers)
    assert response.status_code == 200
    temporary = response.json()["initial_password"]

    stale = await client.get("/api/v1/auth/me", headers=bearer(signed_in["access_token"]))
    assert stale.status_code == 401
    assert (await sign_in(client, "editor@example.org", temporary))["user"][
        "force_password_change"
    ] is True


async def test_me_route_is_not_captured_by_the_user_id_route(client, make_user):
    """A route-order bug made this path unreachable in the code this was ported from."""
    await make_user()
    headers = bearer((await sign_in(client, "editor@example.org", PASSWORD))["access_token"])
    response = await client.patch(
        "/api/v1/users/me", headers=headers, json={"language": "ja", "full_name": "Test Person"}
    )
    assert response.status_code == 200
    assert response.json()["language"] == "ja"
    assert response.json()["full_name"] == "Test Person"


async def test_me_cannot_change_role(client, make_user):
    await make_user("someone@example.org", PASSWORD, UserRole.viewer)
    headers = bearer((await sign_in(client, "someone@example.org", PASSWORD))["access_token"])
    response = await client.patch("/api/v1/users/me", headers=headers, json={"role": "admin"})
    assert response.status_code == 200
    assert response.json()["role"] == "viewer"


async def test_unsupported_language_is_refused(client, make_user):
    await make_user()
    headers = bearer((await sign_in(client, "editor@example.org", PASSWORD))["access_token"])
    response = await client.patch("/api/v1/users/me", headers=headers, json={"language": "de"})
    assert response.status_code == 422


async def test_admins_see_and_change_only_their_own_institution(client, admin_headers):
    async with SessionLocal() as db:
        other = Institution(name_en="Other University", timezone="UTC", settings={})
        db.add(other)
        await db.flush()
        outsider = User(
            institution_id=other.id,
            email="outsider@example.org",
            password_hash=hash_password(PASSWORD),
            role=UserRole.admin,
        )
        db.add(outsider)
        await db.commit()

    listed = (await client.get("/api/v1/users", headers=admin_headers)).json()
    assert "outsider@example.org" not in [user["email"] for user in listed]

    changed = await client.patch(
        f"/api/v1/users/{outsider.id}", headers=admin_headers, json={"is_active": False}
    )
    assert changed.status_code == 404


# ---------------------------------------------------------------- preferences


async def test_a_person_keeps_their_column_choice(client, headers_for):
    headers = await headers_for(UserRole.editor)
    me = (await client.get("/api/v1/auth/me", headers=headers)).json()
    assert me["preferences"]["data_columns"] == {"hidden": [], "shown": []}

    choice = {"data_columns": {"hidden": ["unit"], "shown": ["journal"]}}
    saved = await client.patch("/api/v1/users/me", headers=headers, json={"preferences": choice})
    assert saved.status_code == 200
    assert saved.json()["preferences"]["data_columns"] == choice["data_columns"]
    me = (await client.get("/api/v1/auth/me", headers=headers)).json()
    assert me["preferences"]["data_columns"] == choice["data_columns"]


async def test_preferences_are_checked_and_are_not_a_record_change(client, headers_for):
    headers = await headers_for(UserRole.editor, "tidy@example.org")
    bad = await client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={"preferences": {"data_columns": {"hidden": "unit"}}},
    )
    assert bad.status_code == 422
    await client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={"preferences": {"data_columns": {"hidden": ["unit"]}}},
    )
    async with SessionLocal() as db:
        user_id = await db.scalar(select(User.id).where(User.email == "tidy@example.org"))
        entry = await db.scalar(
            select(AuditLog).where(AuditLog.entity_id == user_id, AuditLog.field == "preferences")
        )
    assert entry is None
