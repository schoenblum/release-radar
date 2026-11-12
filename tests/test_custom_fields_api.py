"""Institution and personal custom fields (BRIEF section 6.6). Synthetic data."""

import pytest
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Release, UserRole

URL = "/api/v1/custom-fields"
NEW_INSTITUTION = {"scope": "institution", "label_en": "Press Run", "field_type": "integer"}
NEW_PERSONAL = {"scope": "personal", "label_en": "My Clicks", "field_type": "integer"}


async def _patch(client, field_id, headers, field, value, version=0):
    return await client.patch(
        f"{URL}/{field_id}",
        headers=headers,
        json={"field": field, "value": value, "version": version},
    )


async def _user_id(client, headers) -> str:
    return (await client.get("/api/v1/auth/me", headers=headers)).json()["id"]


async def test_only_admins_create_institution_fields(client, headers_for):
    admin = await headers_for(UserRole.admin)
    editor = await headers_for(UserRole.editor)
    assert (await client.post(URL, headers=editor, json=NEW_INSTITUTION)).status_code == 403
    response = await client.post(URL, headers=admin, json=NEW_INSTITUTION)
    assert response.status_code == 201
    body = response.json()
    assert body["key"] == "press_run"
    assert body["owner_id"] is None


async def test_editors_and_admins_create_personal_fields_for_themselves(client, headers_for):
    """R6.6.2. Viewers do not."""
    editor = await headers_for(UserRole.editor)
    viewer = await headers_for(UserRole.viewer)
    response = await client.post(URL, headers=editor, json=NEW_PERSONAL)
    assert response.status_code == 201
    assert response.json()["owner_id"] == await _user_id(client, editor)
    assert (await client.post(URL, headers=viewer, json=NEW_PERSONAL)).status_code == 403


async def test_everyone_can_see_every_field_labelled_with_its_owner(client, headers_for):
    editor = await headers_for(UserRole.editor)
    viewer = await headers_for(UserRole.viewer)
    await client.post(URL, headers=editor, json=NEW_PERSONAL)
    rows = (await client.get(URL, headers=viewer)).json()
    assert [(row["label_en"], row["owner_name"], row["owner_active"]) for row in rows] == [
        ("My Clicks", "editor-account@example.org", True)
    ]


async def test_keys_stay_unique(client, admin_headers):
    first = (await client.post(URL, headers=admin_headers, json=NEW_INSTITUTION)).json()
    second = (await client.post(URL, headers=admin_headers, json=NEW_INSTITUTION)).json()
    assert (first["key"], second["key"]) == ("press_run", "press_run_2")


async def test_a_personal_field_cannot_be_required_or_scored(client, admin_headers):
    for extra in ({"required": True}, {"score_eligible": True}):
        response = await client.post(URL, headers=admin_headers, json={**NEW_PERSONAL, **extra})
        assert (response.status_code, response.json()) == (422, {"detail": "field_not_editable"})
    field = (await client.post(URL, headers=admin_headers, json=NEW_PERSONAL)).json()
    response = await _patch(client, field["id"], admin_headers, "required", True)
    assert response.json() == {"detail": "field_not_editable"}


@pytest.mark.parametrize(
    "values",
    [{"field_type": "emoji"}, {"scope": "team"}, {"label_en": "  "}],
)
async def test_invalid_new_fields_are_refused(client, admin_headers, values):
    response = await client.post(URL, headers=admin_headers, json={**NEW_INSTITUTION, **values})
    assert response.status_code == 422


async def test_only_numeric_fields_can_be_scored(client, admin_headers):
    text_field = {**NEW_INSTITUTION, "field_type": "text"}
    made = await client.post(
        URL, headers=admin_headers, json={**text_field, "score_eligible": True}
    )
    assert made.json() == {"detail": "score_eligible_numeric_only"}
    field = (await client.post(URL, headers=admin_headers, json=text_field)).json()
    patched = await _patch(client, field["id"], admin_headers, "score_eligible", True)
    assert patched.json() == {"detail": "score_eligible_numeric_only"}
    number = (await client.post(URL, headers=admin_headers, json=NEW_INSTITUTION)).json()
    assert (await _patch(client, number["id"], admin_headers, "score_eligible", True)).json()[
        "value"
    ] is True


async def test_type_key_and_scope_stay_fixed(client, admin_headers):
    field = (await client.post(URL, headers=admin_headers, json=NEW_INSTITUTION)).json()
    for name in ("field_type", "key", "scope", "owner_id"):
        response = await _patch(client, field["id"], admin_headers, name, "text")
        assert response.json() == {"detail": "field_not_editable"}


async def test_an_institution_field_is_retired_not_deleted(client, admin_headers):
    field = (await client.post(URL, headers=admin_headers, json=NEW_INSTITUTION)).json()
    retired = await _patch(client, field["id"], admin_headers, "is_active", False)
    assert retired.json()["value"] is False
    rows = (await client.get(URL, headers=admin_headers)).json()
    assert [row["is_active"] for row in rows] == [False]
    assert (await client.delete(f"{URL}/{field['id']}", headers=admin_headers)).status_code == 405


async def test_select_options_carry_both_languages(client, admin_headers):
    response = await client.post(
        URL,
        headers=admin_headers,
        json={
            **NEW_INSTITUTION,
            "field_type": "single_select",
            "options": [
                {"label_en": "Wire Service", "label_ja": "通信社"},
                {"label_en": "Newspaper"},
            ],
        },
    )
    assert response.json()["options"] == [
        {"key": "wire_service", "label_en": "Wire Service", "label_ja": "通信社"},
        {"key": "newspaper", "label_en": "Newspaper", "label_ja": None},
    ]
    blank = await client.post(
        URL, headers=admin_headers, json={**NEW_INSTITUTION, "options": [{"label_ja": "名前"}]}
    )
    assert blank.json() == {"detail": "field_required"}


async def test_a_field_can_create_due_items_at_a_checkpoint(client, admin_headers):
    checkpoint = (await client.get("/api/v1/checkpoints", headers=admin_headers)).json()[0]
    field = (
        await client.post(
            URL,
            headers=admin_headers,
            json={**NEW_PERSONAL, "due_checkpoint_id": checkpoint["id"]},
        )
    ).json()
    assert field["due_checkpoint_id"] == checkpoint["id"]
    bad = await client.post(
        URL,
        headers=admin_headers,
        json={**NEW_PERSONAL, "due_checkpoint_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert bad.json() == {"detail": "unknown_reference"}


# ---------------------------------------------------------------- who may edit


async def test_only_the_owner_edits_a_personal_field(client, headers_for):
    admin = await headers_for(UserRole.admin)
    owner = await headers_for(UserRole.editor, "owner@example.org")
    other = await headers_for(UserRole.editor, "other@example.org")
    field = (await client.post(URL, headers=owner, json=NEW_PERSONAL)).json()

    assert (await _patch(client, field["id"], owner, "label_ja", "私の")).status_code == 200
    for headers in (other, admin):
        refused = await _patch(client, field["id"], headers, "label_en", "Taken", 0)
        assert refused.status_code == 403
        assert refused.json() == {"detail": "personal_field_read_only"}


async def test_editors_cannot_edit_institution_fields(client, headers_for):
    admin = await headers_for(UserRole.admin)
    editor = await headers_for(UserRole.editor)
    field = (await client.post(URL, headers=admin, json=NEW_INSTITUTION)).json()
    refused = await _patch(client, field["id"], editor, "label_en", "No")
    assert (refused.status_code, refused.json()) == (403, {"detail": "admin_required"})


async def test_saves_detect_conflicts(client, admin_headers):
    field = (await client.post(URL, headers=admin_headers, json=NEW_INSTITUTION)).json()
    await _patch(client, field["id"], admin_headers, "label_ja", "一")
    stale = await _patch(client, field["id"], admin_headers, "label_ja", "二", 0)
    assert stale.status_code == 409
    assert stale.json()["current_value"] == "一"


async def test_reordering(client, headers_for):
    admin = await headers_for(UserRole.admin)
    editor = await headers_for(UserRole.editor)
    one = (await client.post(URL, headers=admin, json=NEW_INSTITUTION)).json()
    two = (await client.post(URL, headers=admin, json=NEW_INSTITUTION)).json()
    ids = [two["id"], one["id"]]

    assert (
        await client.post(f"{URL}/reorder", headers=editor, json={"ids": ids})
    ).status_code == 403
    assert (
        await client.post(f"{URL}/reorder", headers=admin, json={"ids": ids})
    ).status_code == 204
    rows = (await client.get(URL, headers=admin)).json()
    assert [row["id"] for row in rows] == ids


# ---------------------------------------------------------------- when someone leaves


async def test_a_deactivated_owners_field_stays_visible_and_says_so(client, headers_for):
    """R3.4.3."""
    admin = await headers_for(UserRole.admin)
    owner = await headers_for(UserRole.editor, "owner@example.org")
    await client.post(URL, headers=owner, json=NEW_PERSONAL)
    owner_id = await _user_id(client, owner)
    await client.patch(f"/api/v1/users/{owner_id}", headers=admin, json={"is_active": False})
    rows = (await client.get(URL, headers=admin)).json()
    assert rows[0]["owner_active"] is False


async def test_an_admin_transfers_a_field_to_someone_who_can_edit(client, headers_for):
    admin = await headers_for(UserRole.admin)
    owner = await headers_for(UserRole.editor, "owner@example.org")
    heir = await headers_for(UserRole.editor, "heir@example.org")
    viewer = await headers_for(UserRole.viewer)
    field = (await client.post(URL, headers=owner, json=NEW_PERSONAL)).json()

    denied = await client.post(
        f"{URL}/{field['id']}/transfer",
        headers=owner,
        json={"owner_id": await _user_id(client, heir)},
    )
    assert denied.status_code == 403
    refused = await client.post(
        f"{URL}/{field['id']}/transfer",
        headers=admin,
        json={"owner_id": await _user_id(client, viewer)},
    )
    assert refused.json() == {"detail": "owner_must_edit"}

    moved = await client.post(
        f"{URL}/{field['id']}/transfer",
        headers=admin,
        json={"owner_id": await _user_id(client, heir)},
    )
    assert moved.json()["owner_name"] == "heir@example.org"
    assert (await _patch(client, field["id"], heir, "label_ja", "継承")).status_code == 200
    assert (await _patch(client, field["id"], owner, "label_en", "Mine", 0)).status_code == 403


async def test_converting_to_an_institution_field_keeps_the_values(client, headers_for):
    """R3.4.3: the key stays, and values are stored by key."""
    admin = await headers_for(UserRole.admin)
    owner = await headers_for(UserRole.editor, "owner@example.org")
    field = (await client.post(URL, headers=owner, json=NEW_PERSONAL)).json()
    institution_id = None
    async with SessionLocal() as db:
        from app.models import Institution

        institution_id = await db.scalar(select(Institution.id))
        release = Release(
            institution_id=institution_id,
            title="A release",
            custom_values={field["key"]: {"state": "value", "value": 12}},
        )
        db.add(release)
        await db.commit()

    # Only an admin, or the field's owner (Daniel, 2026-11-12).
    someone = await headers_for(UserRole.editor, "someone@example.org")
    denied = await client.post(f"{URL}/{field['id']}/convert", headers=someone)
    assert denied.json() == {"detail": "personal_field_read_only"}
    converted = (await client.post(f"{URL}/{field['id']}/convert", headers=admin)).json()
    assert converted["scope"] == "institution"
    assert converted["owner_id"] is None
    assert converted["key"] == field["key"]
    async with SessionLocal() as db:
        stored = await db.get(Release, release.id)
    assert stored.custom_values[field["key"]]["value"] == 12
    # Now it behaves like one, and a second conversion has nothing to do.
    again = await client.post(f"{URL}/{field['id']}/convert", headers=admin)
    assert again.json() == {"detail": "field_not_editable"}


async def test_the_owner_can_share_their_own_field(client, headers_for):
    owner = await headers_for(UserRole.editor, "owner@example.org")
    field = (await client.post(URL, headers=owner, json=NEW_PERSONAL)).json()
    shared = (await client.post(f"{URL}/{field['id']}/convert", headers=owner)).json()
    assert (shared["scope"], shared["owner_id"]) == ("institution", None)
    # Shared now, it is the admins' to look after.
    assert (await _patch(client, field["id"], owner, "label_en", "Mine", 0)).status_code == 403
