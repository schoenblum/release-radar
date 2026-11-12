"""Score profiles and the analysis defaults (R8.2, R6.4.2; phase-2 brief §4.3). Synthetic data."""

from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import (
    AuditLog,
    Institution,
    Measure,
    Reading,
    Release,
    ReleaseType,
    ScoreProfile,
    ScoreProfileVersion,
    UserRole,
)
from app.services.readings import today_in

URL = "/api/v1/score-profiles"
DEFAULT_WEIGHTS = {
    "pickups_major": 35,
    "altmetric": 25,
    "ea_views.d28": 15,
    "ea_views.d0": 10,
    "pickups_all": 10,
    "hp_views.d28": 5,
}


def _version(**changes):
    return {
        "name_en": "Reach",
        "name_ja": "広がり",
        "purpose": "How far it went.",
        "weights": {"ea_views.d28": 60, "hp_views.d28": 40},
        "altmetric_basis": "increase",
        "coverage_min": 60,
        "comparison_years": 3,
        "min_values": 10,
        **changes,
    }


async def _seeded(client, headers) -> dict:
    profiles = (await client.get(URL, headers=headers)).json()
    return next(profile for profile in profiles if profile["seeded"])


async def test_every_install_starts_with_news_performance_as_the_default(client, headers_for):
    viewer = await headers_for(UserRole.viewer)
    profiles = (await client.get(URL, headers=viewer)).json()
    assert len(profiles) == 1
    profile = profiles[0]
    assert (profile["key"], profile["is_default"], profile["seeded"]) == (
        "news_performance",
        True,
        True,
    )
    current = profile["current"]
    assert current["version"] == 1
    assert (current["name_en"], current["name_ja"]) == ("News performance", "ニュースでの反響")
    assert current["weights"] == DEFAULT_WEIGHTS
    assert (
        current["altmetric_basis"],
        current["coverage_min"],
        current["comparison_years"],
        current["min_values"],
    ) == ("increase", 60, 3, 10)


async def test_seeding_again_adds_nothing(client, admin_headers):
    from app.bootstrap import bootstrap

    await bootstrap()
    assert len((await client.get(URL, headers=admin_headers)).json()) == 1


async def test_the_components_are_the_dimensions_with_altmetric_once(client, headers_for):
    components = (
        await client.get(f"{URL}/components", headers=await headers_for(UserRole.viewer))
    ).json()
    keys = [item["key"] for item in components]
    assert "altmetric" in keys
    assert not {"altmetric.d0", "altmetric.d28", "altmetric_increase"} & set(keys)
    assert {"ea_views.d28", "hp_views.d28", "pickups_major", "satisfaction", "inquiries"} <= set(
        keys
    )
    allowed = {item["key"]: item["allowed_in_default"] for item in components}
    assert allowed["satisfaction"] is False and allowed["research_outcomes"] is False
    assert allowed["inquiries"] is True


async def test_saving_makes_a_new_version_and_keeps_the_old(client, admin_headers):
    seeded = await _seeded(client, admin_headers)
    weights = {**DEFAULT_WEIGHTS, "altmetric": 20, "hp_views.d28": 10}
    response = await client.post(
        f"{URL}/{seeded['id']}/versions",
        json=_version(name_en="News performance", weights=weights, altmetric_basis="d28"),
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    saved = response.json()
    assert [version["version"] for version in saved["versions"]] == [2, 1]
    assert saved["current"]["weights"] == weights
    assert saved["current"]["altmetric_basis"] == "d28"
    assert saved["current"]["created_by"] == "chief@example.org"
    assert saved["versions"][1]["weights"] == DEFAULT_WEIGHTS
    async with SessionLocal() as db:
        created = await db.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.entity_type == "score_profile_versions", AuditLog.action == "create")
        )
    assert created == 2


@pytest.mark.parametrize(
    ("weights", "code"),
    [
        ({"ea_views.d28": 60, "hp_views.d28": 30}, "profile_weights_total"),
        ({"ea_views.d28": 60, "nonsense": 40}, "profile_component_unknown"),
        ({"altmetric.d28": 60, "hp_views.d28": 40}, "profile_component_unknown"),
        ({"ea_views.d28": 120, "hp_views.d28": -20}, "field_out_of_range"),
    ],
)
async def test_weights_must_be_known_components_totalling_100(client, admin_headers, weights, code):
    seeded = await _seeded(client, admin_headers)
    response = await client.post(
        f"{URL}/{seeded['id']}/versions", json=_version(weights=weights), headers=admin_headers
    )
    assert response.status_code == 422
    assert response.json()["detail"] == code


async def test_satisfaction_goes_into_other_profiles_never_the_seeded_one(client, admin_headers):
    seeded = await _seeded(client, admin_headers)
    weights = {"ea_views.d28": 50, "satisfaction": 50}
    refused = await client.post(
        f"{URL}/{seeded['id']}/versions", json=_version(weights=weights), headers=admin_headers
    )
    assert refused.json()["detail"] == "profile_component_not_in_default"
    created = await client.post(URL, json=_version(weights=weights), headers=admin_headers)
    assert created.status_code == 201
    assert created.json()["is_default"] is False
    assert created.json()["current"]["weights"] == weights


async def test_one_default_at_a_time(client, admin_headers):
    other = (await client.post(URL, json=_version(), headers=admin_headers)).json()
    profiles = (await client.post(f"{URL}/{other['id']}/default", headers=admin_headers)).json()
    defaults = [profile["id"] for profile in profiles if profile["is_default"]]
    assert defaults == [other["id"]]
    assert profiles[0]["id"] == other["id"]


@pytest.mark.parametrize("role", [UserRole.editor, UserRole.viewer])
async def test_only_admins_change_profiles(client, headers_for, admin_headers, role):
    seeded = await _seeded(client, admin_headers)
    headers = await headers_for(role)
    assert (await client.post(URL, json=_version(), headers=headers)).status_code == 403
    assert (
        await client.post(f"{URL}/{seeded['id']}/versions", json=_version(), headers=headers)
    ).status_code == 403
    assert (await client.post(f"{URL}/{seeded['id']}/default", headers=headers)).status_code == 403
    assert (
        await client.post(f"{URL}/preview", json={"version": _version()}, headers=headers)
    ).status_code == 403


async def _views_releases(values: dict[str, int], days_ago: int = 40) -> None:
    """Finished peer-reviewed releases with EurekAlert views, day 28."""
    async with SessionLocal() as db:
        institution = await db.scalar(select(Institution))
        today = today_in(institution.timezone)
        peer = await db.scalar(select(ReleaseType.id).where(ReleaseType.key == "peer_reviewed"))
        for code, views in values.items():
            release = Release(
                institution_id=institution.id,
                title=f"Release {code}",
                code=code,
                release_date=today - timedelta(days=days_ago),
                ea_url=f"https://www.eurekalert.org/news-releases/{abs(hash(code)) % 10**6}",
                release_type_id=peer,
            )
            db.add(release)
            await db.flush()
            reading = await db.scalar(
                select(Reading)
                .join(Measure, Measure.id == Reading.measure_id)
                .where(Reading.release_id == release.id, Measure.key == "ea_views.d28")
            )
            reading.value, reading.state, reading.source = Decimal(views), "value", "manual"
        await db.commit()


async def test_the_preview_shows_the_top_5_under_the_saved_and_the_edited_version(
    client, admin_headers
):
    await _views_releases({f"AY2026-{n:02d}": n * 100 for n in range(1, 8)})
    seeded = await _seeded(client, admin_headers)
    edited = _version(weights={"ea_views.d28": 100}, min_values=1)
    response = await client.post(
        f"{URL}/preview",
        json={"version": edited, "profile_id": seeded["id"]},
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert [row["code"] for row in body["edited"]] == [
        "AY2026-07",
        "AY2026-06",
        "AY2026-05",
        "AY2026-04",
        "AY2026-03",
    ]
    # AY2026-07 has 6 below and itself: (6 + ½) / 7 = 92.86.
    assert body["edited"][0]["score"] == 93
    assert body["edited"][0]["components"] == ["ea_views.d28"]
    # The saved default asks for 10 values per component: with 7 releases nobody has a score.
    assert body["saved"] == [] and body["saved_version"] == 1


async def test_the_analysis_defaults_start_with_peer_reviewed_publications(client, admin_headers):
    settings = (await client.get("/api/v1/settings/institution", headers=admin_headers)).json()
    async with SessionLocal() as db:
        peer = await db.scalar(select(ReleaseType.id).where(ReleaseType.key == "peer_reviewed"))
        feature = await db.scalar(select(ReleaseType.id).where(ReleaseType.key == "feature"))
    assert settings["analysed_release_type_ids"] == [str(peer)]
    assert settings["shown_release_type_ids"] == [str(peer)]

    async def patch(field, value, version):
        return await client.patch(
            "/api/v1/settings/institution",
            json={"field": field, "value": value, "version": version},
            headers=admin_headers,
        )

    both = [str(peer), str(feature)]
    assert (await patch("analysed_release_type_ids", both, 0)).status_code == 200
    assert (await patch("shown_release_type_ids", both, 0)).status_code == 200
    # Shown offers only what analysed includes: taking the feature out of analysed takes it out
    # of shown too.
    assert (await patch("analysed_release_type_ids", [str(peer)], 1)).status_code == 200
    settings = (await client.get("/api/v1/settings/institution", headers=admin_headers)).json()
    assert settings["shown_release_type_ids"] == [str(peer)]
    refused = await patch(
        "shown_release_type_ids", both, settings["field_versions"]["shown_release_type_ids"]
    )
    assert refused.json()["detail"] == "shown_outside_analysed"
    unknown = await patch("analysed_release_type_ids", [str(peer), str(peer)[:-1] + "0"], 2)
    assert unknown.json()["detail"] in {"unknown_reference", "field_invalid"}
    # Empty: every type.
    assert (await patch("analysed_release_type_ids", [], 2)).status_code == 200


async def test_the_full_export_has_the_profiles(client, admin_headers):
    response = await client.get("/api/v1/settings/export?format=json", headers=admin_headers)
    data = response.json()
    assert len(data["score_profiles"]) == 1
    assert data["score_profile_versions"][0]["weights"] == DEFAULT_WEIGHTS


async def test_versions_are_never_rewritten(client, admin_headers):
    seeded = await _seeded(client, admin_headers)
    await client.post(
        f"{URL}/{seeded['id']}/versions", json=_version(name_en="A"), headers=admin_headers
    )
    async with SessionLocal() as db:
        versions = list(
            await db.scalars(
                select(ScoreProfileVersion)
                .where(ScoreProfileVersion.profile_id == seeded["id"])
                .order_by(ScoreProfileVersion.version)
            )
        )
        profile = await db.get(ScoreProfile, seeded["id"])
    assert [v.name_en for v in versions] == ["News performance", "A"]
    assert profile.is_default
