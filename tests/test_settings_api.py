"""Settings: institution, checkpoints, measures, core fields, landing pages. Synthetic data."""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select

from app.database import SessionLocal
from app.models import AuditLog, Institution, Measure, Reading, Release, User, UserRole, Writer
from tests.conftest import bearer, sign_in

PASSWORD = "correct-horse-battery"
INSTITUTION = "/api/v1/settings/institution"


async def _patch(client, url, headers, field, value, version=0):
    return await client.patch(
        url, headers=headers, json={"field": field, "value": value, "version": version}
    )


async def _create_release(**values) -> Release:
    async with SessionLocal() as db:
        institution_id = await db.scalar(select(Institution.id))
        release = Release(institution_id=institution_id, title="A release", **values)
        db.add(release)
        await db.commit()
        return release


async def _state(release: Release, key: str) -> str | None:
    async with SessionLocal() as db:
        return await db.scalar(
            select(Reading.state)
            .join(Measure, Measure.id == Reading.measure_id)
            .where(Reading.release_id == release.id, Measure.key == key)
        )


# ---------------------------------------------------------------- who may do what


@pytest.mark.parametrize("role", [UserRole.editor, UserRole.viewer])
async def test_settings_are_for_admins(client, headers_for, role):
    headers = await headers_for(role)
    assert (await client.get(INSTITUTION, headers=headers)).status_code == 403
    assert (await _patch(client, INSTITUTION, headers, "name_ja", "x")).status_code == 403
    created = await client.post(
        "/api/v1/checkpoints",
        headers=headers,
        json={"values": {"label_en": "Day 90", "offset_days": 90}},
    )
    assert created.status_code == 403


async def test_everyone_signed_in_can_read_what_the_grid_needs(client, headers_for):
    headers = await headers_for(UserRole.viewer)
    for path in ("/api/v1/checkpoints", "/api/v1/measures", "/api/v1/core-fields"):
        assert (await client.get(path, headers=headers)).status_code == 200


# ---------------------------------------------------------------- saving one field


async def test_institution_fields_save_one_at_a_time(client, admin_headers):
    response = await _patch(client, INSTITUTION, admin_headers, "name_ja", "新しい名前")
    assert response.status_code == 200
    assert response.json() == {"field": "name_ja", "value": "新しい名前", "version": 1}
    current = (await client.get(INSTITUTION, headers=admin_headers)).json()
    assert current["name_ja"] == "新しい名前"
    assert current["field_versions"] == {"name_ja": 1}


async def test_a_stale_save_of_the_same_field_is_refused_with_the_current_value(
    client, admin_headers
):
    """R3.3.3: the second person sees what is there now and chooses."""
    await _patch(client, INSTITUTION, admin_headers, "name_ja", "First person")
    response = await _patch(client, INSTITUTION, admin_headers, "name_ja", "Second person", 0)
    assert response.status_code == 409
    assert response.json() == {
        "detail": "conflict",
        "field": "name_ja",
        "current_value": "First person",
        "current_version": 1,
    }
    # Choosing "keep mine" is a save against the version they were just shown.
    keep = await _patch(client, INSTITUTION, admin_headers, "name_ja", "Second person", 1)
    assert keep.json()["version"] == 2


async def test_two_people_changing_different_fields_never_conflict(client, admin_headers):
    """R3.3.2."""
    first = await _patch(client, INSTITUTION, admin_headers, "name_ja", "One", 0)
    second = await _patch(client, INSTITUTION, admin_headers, "contact_email", "a@example.org", 0)
    assert (first.status_code, second.status_code) == (200, 200)


async def test_saving_the_same_value_does_not_raise_the_version(client, admin_headers):
    await _patch(client, INSTITUTION, admin_headers, "name_ja", "Same", 0)
    again = await _patch(client, INSTITUTION, admin_headers, "name_ja", "Same", 1)
    assert again.json()["version"] == 1


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("name_en", "", "field_required"),
        ("name_en", "x" * 256, "field_too_long"),
        ("timezone", "Mars/Olympus", "invalid_timezone"),
        ("ay_start_month", 13, "field_out_of_range"),
        ("ay_start_month", "soon", "field_invalid"),
        ("website_domain", "not a domain", "invalid_domain"),
        ("contact_email", "not an address", "invalid_email"),
        ("release_code_pattern", "AY-{nn}", "invalid_code_pattern"),
        ("release_code_pattern", "AY{yyyy}-{nn}-{other}", "invalid_code_pattern"),
        ("landing_pages", {"admin": "all"}, "field_invalid"),
        ("landing_pages", {"admin": "x", "editor": "all", "viewer": "all"}, "field_invalid"),
        ("major_outlet_threshold", 5, "field_not_editable"),
        ("display_time_zones", ["Mars/Olympus"], "invalid_timezone"),
        ("display_time_zones", "America/New_York", "invalid_timezone"),
        (
            "display_time_zones",
            ["America/New_York", "Europe/London", "UTC", "Europe/Paris"],
            "too_many_time_zones",
        ),
        ("id", "x", "field_not_editable"),
    ],
)
async def test_invalid_values_are_refused_with_a_translatable_reason(
    client, admin_headers, field, value, code
):
    response = await _patch(client, INSTITUTION, admin_headers, field, value)
    assert response.status_code == 422
    assert response.json() == {"detail": code}


async def test_release_times_show_in_up_to_three_further_zones(client, admin_headers, headers_for):
    """Daniel, 2026-11-12. US Eastern to start with, as EurekAlert works in it. Any zone, in
    the order chosen; a place can stay empty."""
    brand = (await client.get("/api/v1/brand")).json()
    assert brand["display_time_zones"] == ["America/New_York"]
    chosen = ["Europe/London", "America/New_York", "Europe/London"]
    saved = await _patch(client, INSTITUTION, admin_headers, "display_time_zones", chosen)
    assert saved.json()["value"] == ["Europe/London", "America/New_York"]
    brand = (await client.get("/api/v1/brand")).json()
    assert brand["display_time_zones"] == ["Europe/London", "America/New_York"]
    # Not on the old list of seven, an empty first place, nothing at the end.
    chosen = [None, "Europe/Berlin", None]
    saved = await _patch(client, INSTITUTION, admin_headers, "display_time_zones", chosen, 1)
    assert saved.json()["value"] == [None, "Europe/Berlin"]
    settings = (await client.get(INSTITUTION, headers=admin_headers)).json()
    assert settings["display_time_zones"] == [None, "Europe/Berlin"]
    # The brand lists the zones to show, in order, without the empty place.
    assert (await client.get("/api/v1/brand")).json()["display_time_zones"] == ["Europe/Berlin"]
    saved = await _patch(client, INSTITUTION, admin_headers, "display_time_zones", [None], 2)
    assert saved.json()["value"] == []


async def test_values_are_cleaned_up(client, admin_headers):
    domain = await _patch(
        client, INSTITUTION, admin_headers, "website_domain", " HTTPS://News.Example.org/path "
    )
    assert domain.json()["value"] == "news.example.org"
    name = await _patch(client, INSTITUTION, admin_headers, "name_ja", "  名前  ")
    assert name.json()["value"] == "名前"
    cleared = await _patch(client, INSTITUTION, admin_headers, "contact_email", "  ")
    assert cleared.json()["value"] is None


async def test_a_change_is_in_the_audit_log_with_the_admin(client, admin_headers):
    await _patch(client, INSTITUTION, admin_headers, "name_ja", "新しい名前")
    async with SessionLocal() as db:
        entry = await db.scalar(select(AuditLog).where(AuditLog.field == "name_ja"))
        chief = await db.scalar(select(User.id).where(User.email == "chief@example.org"))
    assert entry.new_value == "新しい名前"
    assert entry.user_id == chief


# ---------------------------------------------------------------- what rules read


async def test_changing_the_website_domain_re_runs_the_rules(client, admin_headers):
    release = await _create_release(website_url="https://new.example.org/a")
    assert await _state(release, "hp_views.d28") == "not_applicable"

    await _patch(client, INSTITUTION, admin_headers, "website_domain", "new.example.org")
    assert await _state(release, "hp_views.d28") == "missing"

    await _patch(client, INSTITUTION, admin_headers, "website_domain", "other.example.org", 1)
    assert await _state(release, "hp_views.d28") == "not_applicable"


async def test_turning_a_measure_off_and_on_keeps_and_restores_readings(client, admin_headers):
    measures = (await client.get("/api/v1/measures", headers=admin_headers)).json()
    measure = next(m for m in measures if m["key"] == "ea_views.d28")
    url = f"/api/v1/measures/{measure['id']}"

    off = await _patch(client, url, admin_headers, "is_active", False)
    assert off.status_code == 200
    # Created while it is off: no reading.
    release = await _create_release(ea_url="https://www.eurekalert.org/news-releases/1")
    assert await _state(release, "ea_views.d28") is None

    await _patch(client, url, admin_headers, "is_active", True, 1)
    assert await _state(release, "ea_views.d28") == "missing"


async def test_a_collected_from_date_re_runs_the_rules(client, admin_headers):
    release = await _create_release(doi="10.1234/x", release_date=date(2026, 4, 1))
    measures = (await client.get("/api/v1/measures", headers=admin_headers)).json()
    measure = next(m for m in measures if m["key"] == "altmetric.d28")
    await _patch(
        client, f"/api/v1/measures/{measure['id']}", admin_headers, "collected_from", "2026-05-01"
    )
    assert await _state(release, "altmetric.d28") == "not_applicable"


async def test_pickups_go_live_with_their_phase_only(client, admin_headers):
    """R10.10."""
    measures = (await client.get("/api/v1/measures", headers=admin_headers)).json()
    pickups = next(m for m in measures if m["key"] == "pickups_all")
    url = f"/api/v1/measures/{pickups['id']}"
    response = await _patch(client, url, admin_headers, "is_active", True)
    assert response.status_code == 409
    assert response.json() == {"detail": "measure_locked"}
    # The label can still be changed.
    assert (await _patch(client, url, admin_headers, "label_en", "Coverage")).status_code == 200


# ---------------------------------------------------------------- checkpoints and measures


async def test_a_new_checkpoint_and_a_measure_at_it(client, admin_headers):
    release = await _create_release(doi="10.1234/x")
    created = await client.post(
        "/api/v1/checkpoints",
        headers=admin_headers,
        json={"values": {"label_en": "Day 90", "label_ja": "90 日目", "offset_days": 90}},
    )
    assert created.status_code == 201
    checkpoint = created.json()
    assert checkpoint["key"] == "d90"

    measure = await client.post(
        "/api/v1/measures",
        headers=admin_headers,
        json={
            "metric": "altmetric",
            "checkpoint_id": checkpoint["id"],
            "label_en": "Altmetric score, day 90",
        },
    )
    assert measure.status_code == 201
    body = measure.json()
    assert body["key"] == "altmetric.d90"
    assert body["source"] == "manual"
    assert body["applicability"] == "has_doi"
    # Existing releases get a reading straight away.
    assert await _state(release, "altmetric.d90") == "missing"


async def test_a_checkpoint_at_the_same_offset_is_refused(client, admin_headers):
    response = await client.post(
        "/api/v1/checkpoints",
        headers=admin_headers,
        json={"values": {"label_en": "Again", "offset_days": 28}},
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "value_in_use"}


async def test_a_measure_needs_a_known_metric_that_is_not_derived(client, admin_headers):
    checkpoints = (await client.get("/api/v1/checkpoints", headers=admin_headers)).json()
    for metric in ("made_up", "pickups_all"):
        response = await client.post(
            "/api/v1/measures",
            headers=admin_headers,
            json={
                "metric": metric,
                "checkpoint_id": checkpoints[0]["id"],
                "label_en": "Nope",
            },
        )
        assert response.status_code == 422
        assert response.json() == {"detail": "unknown_reference"}


async def test_moving_a_checkpoint_keeps_its_key(client, admin_headers):
    checkpoints = (await client.get("/api/v1/checkpoints", headers=admin_headers)).json()
    d28 = next(c for c in checkpoints if c["key"] == "d28")
    response = await _patch(
        client, f"/api/v1/checkpoints/{d28['id']}", admin_headers, "offset_days", 30
    )
    assert response.json()["value"] == 30
    again = (await client.get("/api/v1/checkpoints", headers=admin_headers)).json()
    assert next(c for c in again if c["id"] == d28["id"])["key"] == "d28"


# ---------------------------------------------------------------- core fields


async def test_core_fields_can_be_relabelled_shown_and_required(client, admin_headers):
    fields = {
        f["key"]: f for f in (await client.get("/api/v1/core-fields", headers=admin_headers)).json()
    }
    notes, time = fields["notes"], fields["release_time"]
    assert (notes["in_record"], notes["in_grid"]) == (True, False)
    assert (time["in_record"], time["in_grid"]) == (True, False)
    url = f"/api/v1/core-fields/{notes['id']}"
    assert (await _patch(client, url, admin_headers, "label_ja", "備考")).json()["value"] == "備考"
    assert (await _patch(client, url, admin_headers, "in_record", False)).json()["value"] is False
    assert (await _patch(client, url, admin_headers, "in_grid", True)).json()["value"] is True
    assert (await _patch(client, url, admin_headers, "required", True)).json()["value"] is True
    # Daniel, 2026-11-12: the release time can be put in everyone's grid.
    url = f"/api/v1/core-fields/{time['id']}"
    assert (await _patch(client, url, admin_headers, "in_grid", True)).json()["value"] is True


@pytest.mark.parametrize(
    ("key", "field"),
    [
        ("code", "in_record"),
        ("code", "in_grid"),
        ("code", "required"),
        ("title", "in_record"),
        ("title", "in_grid"),
        ("release_date", "in_record"),
    ],
)
async def test_core_fields_the_system_relies_on_are_protected(client, admin_headers, key, field):
    """D35: the system assigns the code, so nobody can be asked to fill it in. A record needs
    its code, title and date; a grid its code and title."""
    fields = {
        f["key"]: f for f in (await client.get("/api/v1/core-fields", headers=admin_headers)).json()
    }
    flag = {"in_record": "can_leave_record", "in_grid": "can_leave_grid"}.get(field, "can_require")
    assert fields[key][flag] is False
    response = await _patch(
        client,
        f"/api/v1/core-fields/{fields[key]['id']}",
        admin_headers,
        field,
        field == "required",
    )
    assert response.status_code == 409
    assert fields["release_date"]["can_leave_grid"] is True
    assert response.json() == {"detail": "core_field_locked"}


async def test_core_fields_can_be_reordered_but_only_as_a_complete_list(client, admin_headers):
    fields = (await client.get("/api/v1/core-fields", headers=admin_headers)).json()
    ids = [field["id"] for field in fields]
    new_order = [ids[-1], *ids[:-1]]
    response = await client.post(
        "/api/v1/core-fields/reorder", headers=admin_headers, json={"ids": new_order}
    )
    assert response.status_code == 204
    after = (await client.get("/api/v1/core-fields", headers=admin_headers)).json()
    assert [field["id"] for field in after] == new_order

    partial = await client.post(
        "/api/v1/core-fields/reorder", headers=admin_headers, json={"ids": ids[:3]}
    )
    assert partial.status_code == 422


# ---------------------------------------------------------------- landing pages


async def _landing(client, email: str) -> str:
    return (await sign_in(client, email, PASSWORD))["user"]["landing"]


async def test_landing_follows_the_role_and_needs_releases_of_ones_own_for_mine(client, make_user):
    viewer = await make_user("viewer@example.org", PASSWORD, UserRole.viewer)
    editor = await make_user("writes@example.org", PASSWORD, UserRole.editor)
    starter = await make_user("starter@example.org", PASSWORD, UserRole.editor)
    await make_user("nowriter@example.org", PASSWORD, UserRole.editor)
    async with SessionLocal() as db:
        writer = Writer(
            institution_id=editor.institution_id, display_name_en="A. Writer", user_id=editor.id
        )
        newcomer = Writer(
            institution_id=starter.institution_id, display_name_en="B. Writer", user_id=starter.id
        )
        db.add_all([writer, newcomer])
        await db.flush()
        db.add(Release(institution_id=editor.institution_id, title="Theirs", writer_id=writer.id))
        # A removed release is not something to land on.
        db.add(
            Release(
                institution_id=starter.institution_id,
                title="Gone",
                writer_id=newcomer.id,
                deleted_at=datetime.now(UTC),
            )
        )
        await db.commit()
    assert viewer
    assert await _landing(client, "viewer@example.org") == "analysis"
    assert await _landing(client, "writes@example.org") == "mine"
    # A writer entry with nothing written yet would land on an empty page.
    assert await _landing(client, "starter@example.org") == "all"
    assert await _landing(client, "nowriter@example.org") == "all"


async def test_landing_can_be_configured_per_role(client, admin_headers, make_user):
    await make_user("someone@example.org", PASSWORD, UserRole.editor)
    response = await _patch(
        client,
        INSTITUTION,
        admin_headers,
        "landing_pages",
        {"admin": "all", "editor": "all", "viewer": "all"},
    )
    assert response.status_code == 200
    body = await sign_in(client, "someone@example.org", PASSWORD)
    assert body["user"]["landing"] == "all"
    me = await client.get("/api/v1/auth/me", headers=bearer(body["access_token"]))
    assert me.json()["landing"] == "all"


# ---------------------------------------------------------------- checkpoints before release


async def test_a_checkpoint_can_fall_before_the_release_date(client, admin_headers):
    """R6.5.3, for example to read a score before the release goes out."""
    created = await client.post(
        "/api/v1/checkpoints",
        headers=admin_headers,
        json={"values": {"label_en": "Three days before", "offset_days": -3}},
    )
    assert created.status_code == 201, created.text
    checkpoint = created.json()
    assert (checkpoint["key"], checkpoint["offset_days"]) == ("d-3", -3)
    assert checkpoint["remind_days_before"] == 0

    rows = (await client.get("/api/v1/checkpoints", headers=admin_headers)).json()
    assert [row["offset_days"] for row in rows] == [-3, 0, 28]


async def test_an_existing_checkpoint_can_move_before_the_release_date(client, admin_headers):
    rows = (await client.get("/api/v1/checkpoints", headers=admin_headers)).json()
    d0 = next(row for row in rows if row["key"] == "d0")
    moved = await _patch(
        client, f"/api/v1/checkpoints/{d0['id']}", admin_headers, "offset_days", "-1"
    )
    assert (moved.status_code, moved.json()["value"]) == (200, -1)


@pytest.mark.parametrize("offset", [-366, 3651, "soon"])
async def test_an_offset_stays_within_reason(client, admin_headers, offset):
    response = await client.post(
        "/api/v1/checkpoints",
        headers=admin_headers,
        json={"values": {"label_en": "Far off", "offset_days": offset}},
    )
    assert response.status_code == 422


async def test_a_reminder_goes_out_on_the_day_or_the_day_before(client, admin_headers):
    created = await client.post(
        "/api/v1/checkpoints",
        headers=admin_headers,
        json={"values": {"label_en": "Before", "offset_days": -1, "remind_days_before": 1}},
    )
    assert created.json()["remind_days_before"] == 1
    url = f"/api/v1/checkpoints/{created.json()['id']}"
    version = created.json()["field_versions"].get("remind_days_before", 0)
    back = await _patch(client, url, admin_headers, "remind_days_before", "0", version)
    assert back.json()["value"] == 0
    refused = await _patch(
        client, url, admin_headers, "remind_days_before", 2, back.json()["version"]
    )
    assert refused.status_code == 422
