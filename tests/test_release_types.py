"""Release types (R6.4.1): the list, the institution's default, the field. Synthetic data."""

import csv
import io

import openpyxl
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.bootstrap import bootstrap
from app.database import SessionLocal
from app.models import AuditLog, CoreFieldConfig, Institution, Release, ReleaseType, UserRole
from app.seeds import RELEASE_TYPES

URL = "/api/v1/releases"
LISTS = "/api/v1/lists/release_types"
INSTITUTION = "/api/v1/settings/institution"
EXPORT = "/api/v1/releases/export"


async def _institution() -> Institution:
    async with SessionLocal() as db:
        return await db.scalar(select(Institution).order_by(Institution.created_at))


async def _types(client, headers) -> dict[str, dict]:
    response = await client.get(LISTS, headers=headers)
    assert response.status_code == 200, response.text
    return {row["key"]: row for row in response.json()}


async def _create(client, headers, title="A release"):
    response = await client.post(URL, headers=headers, json={"title": title})
    assert response.status_code == 201, response.text
    return response.json()


async def _patch(client, path, headers, field, value, version):
    return await client.patch(
        path, headers=headers, json={"field": field, "value": value, "version": version}
    )


async def _set_type(client, headers, release, type_id):
    response = await _patch(
        client,
        f"{URL}/{release['id']}",
        headers,
        "release_type_id",
        type_id,
        release["field_versions"].get("release_type_id", 0),
    )
    assert response.status_code == 200, response.text
    return response.json()["release"]


async def _set_default(client, headers, type_id):
    current = (await client.get(INSTITUTION, headers=headers)).json()
    response = await _patch(
        client,
        INSTITUTION,
        headers,
        "default_release_type_id",
        type_id,
        current["field_versions"].get("default_release_type_id", 0),
    )
    assert response.status_code == 200, response.text


async def test_eurekalerts_types_are_seeded_and_peer_reviewed_is_the_default(client, admin_headers):
    types = await _types(client, admin_headers)
    assert list(types) == [key for key, _ in RELEASE_TYPES]
    assert types["peer_reviewed"]["name_en"] == "Peer-reviewed publication"
    assert types["feature"]["name_ja"] == "特集記事"
    assert "Feature stories" in types["feature"]["aliases"]
    assert [row["position"] for row in types.values()] == list(range(len(RELEASE_TYPES)))
    settings = (await client.get(INSTITUTION, headers=admin_headers)).json()
    assert settings["default_release_type_id"] == types["peer_reviewed"]["id"]
    async with SessionLocal() as db:
        order = list(
            await db.scalars(select(CoreFieldConfig.key).order_by(CoreFieldConfig.position))
        )
    assert order.index("release_type") == order.index("field") + 1


async def test_a_new_release_starts_as_the_default_type(client, admin_headers):
    types = await _types(client, admin_headers)
    release = await _create(client, admin_headers)
    assert release["release_type_id"] == types["peer_reviewed"]["id"]
    await _set_default(client, admin_headers, types["feature"]["id"])
    assert (await _create(client, admin_headers))["release_type_id"] == types["feature"]["id"]


async def test_with_no_default_or_a_retired_one_a_release_starts_without_a_type(
    client, admin_headers
):
    types = await _types(client, admin_headers)
    await _set_default(client, admin_headers, None)
    assert (await _create(client, admin_headers))["release_type_id"] is None
    # Seeding again at the next start leaves the admin's choice of none alone.
    await bootstrap()
    assert (await _institution()).default_release_type_id is None

    await _set_default(client, admin_headers, types["business"]["id"])
    business = types["business"]
    response = await _patch(
        client,
        f"{LISTS}/{business['id']}",
        admin_headers,
        "is_active",
        False,
        business["field_versions"].get("is_active", 0),
    )
    assert response.status_code == 200, response.text
    assert (await _create(client, admin_headers))["release_type_id"] is None


async def test_the_type_is_changed_like_any_field_and_audited(client, admin_headers):
    types = await _types(client, admin_headers)
    release = await _create(client, admin_headers)
    changed = await _set_type(client, admin_headers, release, types["feature"]["id"])
    assert changed["release_type_id"] == types["feature"]["id"]
    # A stale version is a conflict, as everywhere.
    stale = await _patch(
        client, f"{URL}/{release['id']}", admin_headers, "release_type_id", None, 0
    )
    assert stale.status_code == 409
    async with SessionLocal() as db:
        entry = await db.scalar(
            select(AuditLog).where(
                AuditLog.entity_id == release["id"], AuditLog.field == "release_type_id"
            )
        )
    assert entry is not None
    assert entry.new_value == types["feature"]["id"]


async def test_a_type_from_elsewhere_or_made_up_is_refused(client, admin_headers):
    release = await _create(client, admin_headers)
    async with SessionLocal() as db:
        other = Institution(name_en="Elsewhere", timezone="Asia/Tokyo", settings={})
        db.add(other)
        await db.flush()
        foreign = ReleaseType(institution_id=other.id, key="x", name_en="X")
        db.add(foreign)
        await db.commit()
        foreign_id = str(foreign.id)
    for value in (foreign_id, "00000000-0000-0000-0000-000000000000", "feature"):
        response = await _patch(
            client, f"{URL}/{release['id']}", admin_headers, "release_type_id", value, 0
        )
        assert response.status_code == 422, (value, response.text)


async def test_the_filter_finds_a_type_or_releases_without_one(client, admin_headers):
    types = await _types(client, admin_headers)
    paper = await _create(client, admin_headers, "Paper")
    feature = await _set_type(
        client,
        admin_headers,
        await _create(client, admin_headers, "Feature"),
        types["feature"]["id"],
    )
    untyped = await _set_type(
        client, admin_headers, await _create(client, admin_headers, "None"), None
    )

    async def titles(value):
        response = await client.get(
            URL, headers=admin_headers, params={"release_type_id": value, "limit": 500}
        )
        assert response.status_code == 200, response.text
        page = response.json()
        return {item["title"] for item in page["items"]}, page["total"], page["view_total"]

    assert await titles(types["feature"]["id"]) == ({feature["title"]}, 1, 3)
    assert await titles(types["peer_reviewed"]["id"]) == ({paper["title"]}, 1, 3)
    assert await titles("none") == ({untyped["title"]}, 1, 3)


async def test_the_export_names_the_type_in_its_language_and_its_filter(client, admin_headers):
    types = await _types(client, admin_headers)
    await _set_type(
        client,
        admin_headers,
        await _create(client, admin_headers, "Feature"),
        types["feature"]["id"],
    )
    await _create(client, admin_headers, "Paper")
    for language, header, names in (
        ("en", "Release type", {"Feature story", "Peer-reviewed publication"}),
        ("ja", "リリースの種類", {"特集記事", "査読付き論文"}),
    ):
        response = await client.post(
            EXPORT, headers=admin_headers, json={"format": "csv", "language": language}
        )
        assert response.status_code == 200, response.text
        rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
        assert {row[header] for row in rows} == names

    response = await client.post(
        EXPORT,
        headers=admin_headers,
        json={"format": "xlsx", "filters": {"view": "all", "release_type_id": "none"}},
    )
    assert response.status_code == 200, response.text
    book = openpyxl.load_workbook(io.BytesIO(response.content))
    notes = [row[0] for row in book[book.sheetnames[-1]].iter_rows(values_only=True)]
    assert any("No release type" in (line or "") for line in notes)
    assert book[book.sheetnames[0]].max_row == 1


async def test_admins_add_rename_and_reorder_types_and_others_only_read(
    client, admin_headers, headers_for
):
    viewer = await headers_for(UserRole.viewer)
    assert len(await _types(client, viewer)) == len(RELEASE_TYPES)
    refused = await client.post(LISTS, headers=viewer, json={"values": {"name_en": "Obituary"}})
    assert refused.status_code == 403

    response = await client.post(
        LISTS, headers=admin_headers, json={"values": {"name_en": "Obituary"}}
    )
    assert response.status_code == 201, response.text
    added = response.json()
    assert added["key"] == "obituary"
    assert added["position"] == len(RELEASE_TYPES)

    feature = (await _types(client, admin_headers))["feature"]
    response = await _patch(client, f"{LISTS}/{feature['id']}", admin_headers, "position", -1, 0)
    assert response.status_code == 422
    response = await _patch(client, f"{LISTS}/{feature['id']}", admin_headers, "position", 0, 0)
    assert response.status_code == 200, response.text
    keys = list(await _types(client, admin_headers))
    assert keys.index("feature") < keys.index("reports_proceedings")


async def test_the_type_list_round_trips_through_csv(client, admin_headers):
    response = await client.get(f"{LISTS}/export", headers=admin_headers)
    assert response.status_code == 200, response.text
    text = response.content.decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))
    assert rows[0] == {
        "key": "peer_reviewed",
        "name_en": "Peer-reviewed publication",
        "name_ja": "査読付き論文",
        "aliases": "Peer-reviewed publications, Peer-reviewed, Paper",
        "position": "0",
        "active": "Y",
    }
    # Two columns: a renamed type and a new one, which goes last; nothing else changes.
    upload = "key,name_ja\r\nfeature,フィーチャー\r\nobituary,\r\n"
    response = await client.post(
        f"{LISTS}/import", headers=admin_headers, json={"csv": upload, "dry_run": False}
    )
    assert response.status_code == 200, response.text
    assert response.json()["created"] == 1
    assert response.json()["updated"] == 1
    types = await _types(client, admin_headers)
    assert types["feature"]["name_ja"] == "フィーチャー"
    assert types["feature"]["name_en"] == "Feature story"
    assert types["obituary"]["name_en"] == "obituary"
    assert types["obituary"]["position"] == len(RELEASE_TYPES)


async def test_only_admins_choose_the_default_and_only_from_this_institution(
    client, admin_headers, headers_for
):
    editor = await headers_for(UserRole.editor)
    response = await _patch(client, INSTITUTION, editor, "default_release_type_id", None, 0)
    assert response.status_code == 403
    response = await _patch(
        client,
        INSTITUTION,
        admin_headers,
        "default_release_type_id",
        "00000000-0000-0000-0000-000000000000",
        0,
    )
    assert response.status_code == 422


async def test_a_type_in_use_cannot_be_deleted_from_the_database(client, admin_headers):
    """Retired, never deleted: releases refer to it (RESTRICT)."""
    await _create(client, admin_headers)
    async with SessionLocal() as db:
        kind = await db.scalar(select(ReleaseType).where(ReleaseType.key == "peer_reviewed"))
        institution = await db.get(Institution, kind.institution_id)
        institution.default_release_type_id = None
        await db.flush()
        assert await db.scalar(select(Release.id).where(Release.release_type_id == kind.id))
        await db.delete(kind)
        with pytest.raises(IntegrityError):
            await db.flush()
