"""The release API (step 1.4). All data here is synthetic."""

import asyncio
from datetime import date, timedelta

import httpx
import pytest
from sqlalchemy import select

from app.database import SessionLocal
from app.models import (
    AuditLog,
    Checkpoint,
    CoreFieldConfig,
    Institution,
    Measure,
    Release,
    Researcher,
    ResearchField,
    Unit,
    User,
    UserRole,
    Writer,
)
from app.services import crossref
from app.services.readings import today_in
from app.services.release_codes import academic_year, format_code

URL = "/api/v1/releases"
DOI = "10.1234/example.5678"
WORK = {
    "title": ["A <i>synthetic</i> paper &amp; its results"],
    "container-title": ["Journal of Examples"],
    "published": {"date-parts": [[2026, 3, 9]]},
    "author": [
        {"given": "Test", "family": "Person", "ORCID": "http://orcid.org/0000-0001-2345-678X"},
        {"name": "Example Consortium"},
    ],
}


async def _create(client, headers, title="A release", **values):
    response = await client.post(URL, headers=headers, json={"title": title, **values})
    assert response.status_code == 201, response.text
    return response.json()


async def _patch(client, release, headers, field, value, version=None):
    version = release["field_versions"].get(field, 0) if version is None else version
    return await client.patch(
        f"{URL}/{release['id']}",
        headers=headers,
        json={"field": field, "value": value, "version": version},
    )


async def _set(client, release, headers, field, value):
    response = await _patch(client, release, headers, field, value)
    assert response.status_code == 200, response.text
    return response.json()["release"]


def _reading(release, key):
    return next(item for item in release["readings"] if item["measure_key"] == key)


async def _enter(client, reading, headers, **body):
    return await client.patch(
        f"/api/v1/readings/{reading['id']}",
        headers=headers,
        json={"version": reading["version"], **body},
    )


async def _institution() -> Institution:
    async with SessionLocal() as db:
        return await db.scalar(select(Institution).order_by(Institution.created_at))


async def _add(*rows):
    """Add list entries directly, for the lists are not what is being tested here."""
    async with SessionLocal() as db:
        db.add_all(rows)
        await db.commit()
    return rows[0] if len(rows) == 1 else rows


async def _link_writer(email: str, name: str = "A. Writer") -> Writer:
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == email))
        writer = Writer(institution_id=user.institution_id, display_name_en=name, user_id=user.id)
        db.add(writer)
        await db.commit()
        return writer


# ---------------------------------------------------------------- who may do what


async def test_viewers_read_and_editors_and_admins_change(client, headers_for):
    admin = await headers_for(UserRole.admin)
    editor = await headers_for(UserRole.editor)
    viewer = await headers_for(UserRole.viewer)
    made = await _create(client, editor)
    await _create(client, admin, title="Another")

    assert (await client.get(URL, headers=viewer)).json()["total"] == 2
    assert (await client.get(f"{URL}/{made['id']}", headers=viewer)).status_code == 200
    assert (await client.get(f"{URL}/{made['id']}/history", headers=viewer)).status_code == 200

    assert (await client.post(URL, headers=viewer, json={"title": "No"})).status_code == 403
    assert (await _patch(client, made, viewer, "notes", "No")).status_code == 403
    assert (await client.delete(f"{URL}/{made['id']}", headers=viewer)).status_code == 403
    assert (
        await client.post(f"{URL}/{made['id']}/crossref", headers=viewer, json={})
    ).status_code == 403
    assert (
        await client.post("/api/v1/lookup/doi", headers=viewer, json={"doi": DOI})
    ).status_code == 403
    reading = _reading(made, "ea_views.d28")
    assert (await _enter(client, reading, viewer, value=1)).status_code == 403


async def test_nothing_without_signing_in(client):
    assert (await client.get(URL)).status_code == 401


async def test_records_of_another_institution_are_out_of_reach(client, admin_headers):
    async with SessionLocal() as db:
        other = Institution(name_en="Other University", timezone="UTC", settings={})
        db.add(other)
        await db.flush()
        foreign = Release(institution_id=other.id, title="Elsewhere")
        foreign_unit = Unit(institution_id=other.id, key="Far", name_en="Far")
        db.add_all([foreign, foreign_unit])
        await db.commit()

    assert (await client.get(URL, headers=admin_headers)).json()["items"] == []
    assert (await client.get(f"{URL}/{foreign.id}", headers=admin_headers)).status_code == 404
    response = await client.patch(
        f"{URL}/{foreign.id}",
        headers=admin_headers,
        json={"field": "notes", "value": "No", "version": 0},
    )
    assert response.status_code == 404
    mine = await _create(client, admin_headers)
    bad = await _patch(client, mine, admin_headers, "unit_id", str(foreign_unit.id))
    assert (bad.status_code, bad.json()) == (422, {"detail": "unknown_reference"})


# ---------------------------------------------------------------- creating


async def test_a_draft_needs_only_a_title(client, admin_headers):
    """R7.5.6."""
    made = await _create(client, admin_headers)
    assert made["title"] == "A release"
    assert made["code"] is None
    assert made["release_date"] is None
    assert made["crossref"] is None
    assert made["academic_year"] is None
    assert {item["measure_key"] for item in made["readings"]} == {
        "ea_views.d0",
        "ea_views.d28",
        "altmetric.d0",
        "altmetric.d28",
        "hp_views.d28",
    }


async def test_a_release_needs_a_title_or_a_doi(client, admin_headers):
    for body in ({}, {"title": "  "}, {"title": None, "doi": ""}):
        response = await client.post(URL, headers=admin_headers, json=body)
        assert (response.status_code, response.json()) == (
            422,
            {"detail": "title_or_doi_required"},
        )


async def test_a_doi_alone_creates_a_release_and_crossref_fills_the_paper(
    client, admin_headers, crossref_answers
):
    """R7.5.4."""
    crossref_answers["works"][DOI] = WORK
    response = await client.post(
        URL, headers=admin_headers, json={"doi": f"  https://doi.org/{DOI.upper()} "}
    )
    assert response.status_code == 201, response.text
    made = response.json()
    assert made["doi"] == DOI
    assert made["title"] is None
    assert made["crossref"] == "found"
    assert made["journal"] == "Journal of Examples"
    assert made["paper_title"] == "A synthetic paper & its results"
    assert made["publication_date"] == "2026-03-09"
    assert made["authors"] == [
        {"given": "Test", "family": "Person", "name": None, "orcid": "0000-0001-2345-678X"},
        {"given": None, "family": None, "name": "Example Consortium", "orcid": None},
    ]


@pytest.mark.parametrize(("status", "said"), [(404, "not_found"), (503, "unavailable")])
async def test_a_failed_lookup_never_stops_a_release(
    client, admin_headers, crossref_answers, status, said
):
    crossref_answers["status"] = status
    made = (await client.post(URL, headers=admin_headers, json={"doi": DOI})).json()
    assert made["crossref"] == said
    assert made["doi"] == DOI
    assert made["journal"] is None


@pytest.mark.parametrize("bad", ["not a doi", "10.12/too-short", "https://example.org/10.1234/x"])
async def test_a_bad_doi_is_explained(client, admin_headers, bad):
    response = await client.post(URL, headers=admin_headers, json={"doi": bad})
    assert (response.status_code, response.json()) == (422, {"detail": "invalid_doi"})


@pytest.mark.parametrize(
    "written",
    [
        "10.1234/Example.5678",
        "https://doi.org/10.1234/example.5678",
        "http://dx.doi.org/10.1234/example.5678",
        "https://www.doi.org/10.1234/example.5678",
        "doi:10.1234/example.5678",
        "DOI: https://doi.org/10.1234/example.5678.",
        "https://doi.org/10.1234%2Fexample.5678",
    ],
)
async def test_a_doi_saves_bare_however_it_was_pasted(client, admin_headers, written):
    """R7.5.7, and Daniel's ask of 2026-11-09: a bare DOI or a link to it, alike."""
    release = await _create(client, admin_headers)
    saved = await _set(client, release, admin_headers, "doi", written)
    assert saved["doi"] == DOI


async def test_the_writer_defaults_to_the_person_creating_it(client, headers_for):
    editor = await headers_for(UserRole.editor, "writer@example.org")
    writer = await _link_writer("writer@example.org")
    assert (await _create(client, editor))["writer_id"] == str(writer.id)


async def test_with_no_writer_entry_the_writer_stays_empty(client, admin_headers):
    assert (await _create(client, admin_headers))["writer_id"] is None


# ---------------------------------------------------------------- saving one field


async def test_fields_save_one_at_a_time_with_conflicts(client, admin_headers):
    """R3.3.2, R3.3.3."""
    made = await _create(client, admin_headers)
    saved = await _patch(client, made, admin_headers, "notes", "First")
    assert saved.status_code == 200
    assert (saved.json()["value"], saved.json()["version"]) == ("First", 1)

    stale = await _patch(client, made, admin_headers, "notes", "Second", 0)
    assert stale.status_code == 409
    assert stale.json() == {
        "detail": "conflict",
        "field": "notes",
        "current_value": "First",
        "current_version": 1,
    }
    # Someone else's change to another field is no conflict.
    other = await _patch(client, made, admin_headers, "also_featured", "Someone", 0)
    assert other.status_code == 200
    current = (await client.get(f"{URL}/{made['id']}", headers=admin_headers)).json()
    assert (current["notes"], current["also_featured"]) == ("First", "Someone")


async def test_an_invalid_value_leaves_everything_else_alone(client, admin_headers):
    made = await _create(client, admin_headers)
    await _set(client, made, admin_headers, "notes", "Kept")
    bad = await _patch(client, made, admin_headers, "release_date", "someday")
    assert (bad.status_code, bad.json()) == (422, {"detail": "field_invalid"})
    current = (await client.get(f"{URL}/{made['id']}", headers=admin_headers)).json()
    assert current["notes"] == "Kept"
    assert current["release_date"] is None


async def test_the_code_cannot_be_edited(client, admin_headers):
    """D35."""
    made = await _create(client, admin_headers)
    response = await _patch(client, made, admin_headers, "code", "AY2026-99")
    assert (response.status_code, response.json()) == (422, {"detail": "field_not_editable"})


async def test_the_model_refuses_to_change_a_code(client, admin_headers):
    """D35, for code that does not come through the API, such as the importer."""
    institution = await _institution()
    release = Release(institution_id=institution.id, title="Fixed", code="AY2026-01")
    release.code = "AY2026-01"
    with pytest.raises(ValueError, match="never changes"):
        release.code = "AY2026-02"


async def test_title_or_doi_stays_true(client, admin_headers, crossref_answers):
    made = await _create(client, admin_headers)
    refused = await _patch(client, made, admin_headers, "title", " ")
    assert (refused.status_code, refused.json()) == (422, {"detail": "title_or_doi_required"})
    with_doi = await _set(client, made, admin_headers, "doi", DOI)
    without_title = await _set(client, with_doi, admin_headers, "title", None)
    assert without_title["title"] is None
    refused = await _patch(client, without_title, admin_headers, "doi", "")
    assert refused.status_code == 422


async def test_saving_the_same_value_is_not_a_change(client, admin_headers):
    made = await _create(client, admin_headers)
    await _set(client, made, admin_headers, "notes", "Same")
    again = await _patch(client, made, admin_headers, "notes", "  Same  ", 1)
    assert again.json()["version"] == 1


async def test_spaces_around_values_go_everywhere(client, admin_headers):
    """R7.5.8."""
    made = await _create(client, admin_headers, title="  A title  ")
    assert made["title"] == "A title"
    saved = await _set(client, made, admin_headers, "ea_url", "  https://example.org/a  ")
    assert saved["ea_url"] == "https://example.org/a"
    saved = await _set(client, made, admin_headers, "release_date", " 2026-05-01 ")
    assert saved["release_date"] == "2026-05-01"


@pytest.mark.parametrize(
    ("written", "stored"),
    [("  0:10", "00:10:00"), ("09:30", "09:30:00"), ("23:59:30", "23:59:30"), ("", None)],
)
async def test_the_release_time_takes_what_a_paste_brings(client, admin_headers, written, stored):
    made = await _create(client, admin_headers)
    saved = await _set(client, made, admin_headers, "release_time", written)
    assert saved["release_time"] == stored


EASTERN = "America/New_York"


async def test_a_date_and_time_in_us_eastern_are_kept_in_japan_time(client, admin_headers):
    """Daniel, 2026-11-12: EurekAlert's date and time, converted; the date can move."""
    made = await _create(client, admin_headers)
    value = {"date": "2026-11-10", "time": "10:00", "zone": EASTERN}
    saved = await _set(client, made, admin_headers, "release_date", value)
    assert (saved["release_date"], saved["release_time"]) == ("2026-11-11", "00:00:00")
    # Summer time: 11:00 EDT is midnight in Japan.
    value = {"date": "2026-08-13", "time": "11:00", "zone": EASTERN}
    saved = await _set(client, saved, admin_headers, "release_date", value)
    assert (saved["release_date"], saved["release_time"]) == ("2026-08-14", "00:00:00")


async def test_a_time_in_us_eastern_goes_with_the_eastern_date(client, admin_headers):
    made = await _create(client, admin_headers)
    saved = await _set(client, made, admin_headers, "release_date", "2026-11-10")
    # The date was typed as it was given, with no time yet: it is the Eastern date.
    zoned = {"time": "10:00", "zone": EASTERN}
    saved = await _set(client, saved, admin_headers, "release_time", zoned)
    assert (saved["release_date"], saved["release_time"]) == ("2026-11-11", "00:00:00")
    # Corrected later, still in Eastern time: the release's Eastern date is still the 10th.
    zoned = {"time": "11:00", "zone": EASTERN}
    saved = await _set(client, saved, admin_headers, "release_time", zoned)
    assert (saved["release_date"], saved["release_time"]) == ("2026-11-11", "01:00:00")
    # A new date in Eastern time keeps the release's Eastern time.
    saved = await _set(
        client, saved, admin_headers, "release_date", {"date": "2026-11-12", "zone": EASTERN}
    )
    assert (saved["release_date"], saved["release_time"]) == ("2026-11-13", "01:00:00")


async def test_a_zoned_time_needs_its_date(client, admin_headers):
    made = await _create(client, admin_headers)
    zoned = {"time": "10:00", "zone": EASTERN}
    bad = await _patch(client, made, admin_headers, "release_time", zoned)
    assert (bad.status_code, bad.json()) == (422, {"detail": "release_date_first"})
    zoned = {"time": "10:00", "zone": "Mars"}
    bad = await _patch(client, made, admin_headers, "release_time", zoned)
    assert (bad.status_code, bad.json()) == (422, {"detail": "invalid_timezone"})


async def test_a_time_the_clocks_skip_is_refused_and_a_repeated_one_is_the_first(
    client, admin_headers
):
    """Daniel, 2026-11-13: a conversion must be true for its date. US daylight saving starts on
    8 March 2026, when 02:00 becomes 03:00: 02:30 never happens. It ends on 1 November, when
    01:30 happens twice: the first, still in daylight saving (UTC−4), is 14:30 in Japan."""
    made = await _create(client, admin_headers)
    skipped = {"date": "2026-03-08", "time": "02:30", "zone": EASTERN}
    bad = await _patch(client, made, admin_headers, "release_date", skipped)
    assert (bad.status_code, bad.json()) == (422, {"detail": "time_skipped"})
    twice = {"date": "2026-11-01", "time": "01:30", "zone": EASTERN}
    saved = await _set(client, made, admin_headers, "release_date", twice)
    assert (saved["release_date"], saved["release_time"]) == ("2026-11-01", "14:30:00")
    # The days either side of the switch, each with its own offset.
    value = {"date": "2026-03-06", "time": "10:00", "zone": EASTERN}
    saved = await _set(client, saved, admin_headers, "release_date", value)
    assert (saved["release_date"], saved["release_time"]) == ("2026-03-07", "00:00:00")
    value = {"date": "2026-03-09", "time": "10:00", "zone": EASTERN}
    saved = await _set(client, saved, admin_headers, "release_date", value)
    assert (saved["release_date"], saved["release_time"]) == ("2026-03-09", "23:00:00")


async def test_a_date_and_time_in_japan_time_stay_as_they_are(client, admin_headers):
    made = await _create(client, admin_headers)
    value = {"date": "2026-11-10", "time": "14:10", "zone": "Asia/Tokyo"}
    saved = await _set(client, made, admin_headers, "release_date", value)
    assert (saved["release_date"], saved["release_time"]) == ("2026-11-10", "14:10:00")
    stale = await _patch(client, made, admin_headers, "release_date", value, version=0)
    assert stale.status_code == 409


@pytest.mark.parametrize("written", ["soon", "25:00", "9", 930])
async def test_a_bad_time_is_explained(client, admin_headers, written):
    made = await _create(client, admin_headers)
    bad = await _patch(client, made, admin_headers, "release_time", written)
    assert (bad.status_code, bad.json()) == (422, {"detail": "invalid_time"})


@pytest.mark.parametrize(
    "written",
    ["not an address", "javascript:alert(1)", "ftp://example.org/x", "https://exa mple.org"],
)
async def test_only_web_addresses_are_kept(client, admin_headers, written):
    made = await _create(client, admin_headers)
    bad = await _patch(client, made, admin_headers, "website_url", written)
    assert (bad.status_code, bad.json()) == (422, {"detail": "invalid_url"})


async def test_an_address_without_a_scheme_gets_one(client, admin_headers):
    made = await _create(client, admin_headers)
    saved = await _set(client, made, admin_headers, "website_url", "news.example.org/a")
    assert saved["website_url"] == "https://news.example.org/a"


async def test_unusual_links_are_saved_with_a_warning(client, admin_headers):
    """R7.5.8: warn, never block. The institution's site here is news.example.org."""
    made = await _create(client, admin_headers)
    assert made["warnings"] == []
    saved = await _set(
        client, made, admin_headers, "ea_url", "https://www.eurekalert.org/news-releases/1234"
    )
    assert saved["warnings"] == []
    saved = await _set(client, saved, admin_headers, "ea_url", "https://www.eurekalert.org/other")
    assert saved["ea_url"] == "https://www.eurekalert.org/other"
    assert saved["warnings"] == ["ea_url_unusual"]
    saved = await _set(client, saved, admin_headers, "website_url", "https://news.example.org/a")
    assert saved["warnings"] == ["ea_url_unusual"]
    saved = await _set(client, saved, admin_headers, "website_url", "https://old.example.org/a")
    assert saved["warnings"] == ["ea_url_unusual", "website_off_domain"]
    assert _reading(saved, "hp_views.d28")["state"] == "not_applicable"


async def test_the_top_page_and_its_position_stay_consistent(client, admin_headers):
    made = await _create(client, admin_headers)
    placed = await _set(client, made, admin_headers, "ea_top_position", "2")
    assert (placed["ea_top_page"], placed["ea_top_position"]) == (True, 2)
    off = await _set(client, placed, admin_headers, "ea_top_page", False)
    assert (off["ea_top_page"], off["ea_top_position"]) == (False, None)
    bad = await _patch(client, off, admin_headers, "ea_top_position", 0)
    assert bad.status_code == 422


async def test_authors_can_be_edited_by_hand(client, admin_headers):
    made = await _create(client, admin_headers)
    saved = await _set(
        client, made, admin_headers, "authors", ["Test Person", {"given": "Other", "family": "One"}]
    )
    assert saved["authors"] == [
        {"given": None, "family": None, "name": "Test Person", "orcid": None},
        {"given": "Other", "family": "One", "name": None, "orcid": None},
    ]
    bad = await _patch(client, saved, admin_headers, "authors", [{"orcid": "x"}])
    assert bad.status_code == 422


async def test_every_change_reaches_the_audit_log_with_the_person(client, admin_headers):
    """R3.4.4."""
    made = await _create(client, admin_headers)
    await _set(client, made, admin_headers, "notes", "Logged")
    async with SessionLocal() as db:
        chief = await db.scalar(select(User.id).where(User.email == "chief@example.org"))
        entry = await db.scalar(
            select(AuditLog).where(AuditLog.entity_id == made["id"], AuditLog.field == "notes")
        )
    assert (entry.old_value, entry.new_value, entry.user_id) == (None, "Logged", chief)


# ---------------------------------------------------------------- defaults that follow


async def _unit_with_field(name="School of Testing"):
    institution = await _institution()
    async with SessionLocal() as db:
        field = ResearchField(institution_id=institution.id, name_en=f"Field of {name}")
        db.add(field)
        await db.flush()
        unit = Unit(
            institution_id=institution.id, key=name, name_en=name, default_field_id=field.id
        )
        db.add(unit)
        await db.commit()
    return unit, field


async def test_unit_and_field_follow_the_researcher(client, admin_headers):
    """R7.5.4."""
    unit, field = await _unit_with_field()
    researcher = await _add(
        Researcher(
            institution_id=(await _institution()).id, name="Test Person", current_unit_id=unit.id
        )
    )
    made = await _create(client, admin_headers)
    saved = await _set(client, made, admin_headers, "researcher_id", str(researcher.id))
    assert saved["researcher_name"] == "Test Person"
    assert saved["unit_id"] == str(unit.id)
    assert saved["field_id"] == str(field.id)
    # A stale screen is told about the values that followed.
    assert saved["field_versions"]["unit_id"] == 1
    assert saved["field_versions"]["field_id"] == 1


async def test_a_choice_someone_made_is_never_overwritten(client, admin_headers):
    """D7: the unit is a snapshot, and a person's choice stands."""
    unit, _ = await _unit_with_field()
    chosen, chosen_field = await _unit_with_field("Chosen School")
    researcher = await _add(
        Researcher(
            institution_id=(await _institution()).id, name="Test Person", current_unit_id=unit.id
        )
    )
    made = await _create(client, admin_headers)
    saved = await _set(client, made, admin_headers, "unit_id", str(chosen.id))
    assert saved["field_id"] == str(chosen_field.id)
    saved = await _set(client, saved, admin_headers, "researcher_id", str(researcher.id))
    assert saved["unit_id"] == str(chosen.id)
    assert saved["field_id"] == str(chosen_field.id)


async def test_the_researchers_gender_is_shown_and_changed_with_the_release(
    client, admin_headers, headers_for
):
    """Daniel, 2026-11-08: gender in the grid. It is the researcher's, so every release follows."""
    institution = await _institution()
    researcher = await _add(Researcher(institution_id=institution.id, name="Test Person"))
    first = await _set(
        client,
        await _create(client, admin_headers),
        admin_headers,
        "researcher_id",
        str(researcher.id),
    )
    second = await _set(
        client,
        await _create(client, admin_headers),
        admin_headers,
        "researcher_id",
        str(researcher.id),
    )
    # Not recorded reads as empty, at the researcher's version.
    assert first["researcher_gender"] is None
    assert first["field_versions"]["researcher_gender"] == 0

    saved = await _patch(client, first, admin_headers, "researcher_gender", "F")
    assert saved.status_code == 200, saved.text
    assert (saved.json()["value"], saved.json()["version"]) == ("F", 1)
    assert saved.json()["release"]["researcher_gender"] == "F"
    shown = (await client.get(f"{URL}/{second['id']}", headers=admin_headers)).json()
    assert shown["researcher_gender"] == "F"
    assert shown["field_versions"]["researcher_gender"] == 1
    async with SessionLocal() as db:
        assert (await db.get(Researcher, researcher.id)).gender == "F"
        logged = await db.scalar(
            select(AuditLog).where(AuditLog.entity_id == researcher.id, AuditLog.field == "gender")
        )
        assert logged is not None

    # Someone working from the old screen is told, at the version they missed.
    stale = await _patch(client, second, admin_headers, "researcher_gender", "M")
    assert stale.status_code == 409
    assert stale.json()["current_version"] == 1

    # Empty means not recorded again; anything else is refused.
    cleared = await _patch(client, shown, admin_headers, "researcher_gender", "")
    assert cleared.json()["release"]["researcher_gender"] is None
    bad = await _patch(client, cleared.json()["release"], admin_headers, "researcher_gender", "x")
    assert bad.status_code == 422

    viewer = await headers_for(UserRole.viewer)
    refused = await _patch(client, shown, viewer, "researcher_gender", "M")
    assert refused.status_code == 403


async def test_a_gender_needs_a_researcher_first(client, admin_headers):
    made = await _create(client, admin_headers)
    assert made["researcher_gender"] is None
    response = await _patch(client, made, admin_headers, "researcher_gender", "F")
    assert (response.status_code, response.json()["detail"]) == (422, "gender_needs_researcher")


async def test_a_merged_researcher_cannot_be_chosen(client, admin_headers):
    institution = await _institution()
    survivor = await _add(Researcher(institution_id=institution.id, name="Survivor"))
    merged = await _add(
        Researcher(institution_id=institution.id, name="Merged", merged_into_id=survivor.id)
    )
    made = await _create(client, admin_headers)
    bad = await _patch(client, made, admin_headers, "researcher_id", str(merged.id))
    assert (bad.status_code, bad.json()) == (409, {"detail": "researcher_merged"})


async def test_changing_the_writer_moves_the_release_between_people(client, headers_for):
    """R7.5.2: due items follow the writer, because they are computed from it."""
    one = await headers_for(UserRole.editor, "one@example.org")
    two = await headers_for(UserRole.editor, "two@example.org")
    await _link_writer("one@example.org", "One")
    second = await _link_writer("two@example.org", "Two")
    made = await _create(client, one)
    assert (await client.get(URL, headers=one, params={"view": "mine"})).json()["total"] == 1
    await _set(client, made, one, "writer_id", str(second.id))
    assert (await client.get(URL, headers=one, params={"view": "mine"})).json()["total"] == 0
    assert (await client.get(URL, headers=two, params={"view": "mine"})).json()["total"] == 1


# ---------------------------------------------------------------- required fields


async def _require(key: str, *, in_record: bool = True) -> None:
    async with SessionLocal() as db:
        config = await db.scalar(select(CoreFieldConfig).where(CoreFieldConfig.key == key))
        config.required = True
        config.in_record = in_record
        await db.commit()


async def test_a_required_field_can_stay_empty_on_a_draft_but_cannot_be_emptied(
    client, admin_headers
):
    """R7.5.6 keeps a draft creatable. Settings' "required" stops a value being cleared."""
    await _require("journal")
    await _require("writer")
    made = await _create(client, admin_headers)
    assert made["missing_required"] == ["writer", "journal"]

    saved = await _set(client, made, admin_headers, "journal", "Journal of Examples")
    assert saved["missing_required"] == ["writer"]
    bad = await _patch(client, saved, admin_headers, "journal", "")
    assert (bad.status_code, bad.json()) == (422, {"detail": "field_required"})
    current = (await client.get(f"{URL}/{made['id']}", headers=admin_headers)).json()
    assert current["journal"] == "Journal of Examples"


async def test_a_field_off_the_record_is_not_asked_for(client, admin_headers):
    await _require("journal", in_record=False)
    assert (await _create(client, admin_headers))["missing_required"] == []


# ---------------------------------------------------------------- codes


async def test_a_release_gets_its_code_when_its_date_is_first_entered(client, admin_headers):
    """D35."""
    made = await _create(client, admin_headers)
    saved = await _set(client, made, admin_headers, "release_date", "2026-04-09")
    assert saved["code"] == "AY2026-01"
    assert saved["academic_year"] == 2026


@pytest.mark.parametrize(
    ("day", "code"), [("2026-03-31", "AY2025-01"), ("2026-04-01", "AY2026-01")]
)
async def test_the_academic_year_turns_over_in_its_start_month(client, admin_headers, day, code):
    made = await _create(client, admin_headers)
    assert (await _set(client, made, admin_headers, "release_date", day))["code"] == code


def test_the_academic_year_follows_the_institution():
    assert academic_year(date(2026, 3, 31), 4) == 2025
    assert academic_year(date(2026, 4, 1), 4) == 2026
    assert academic_year(date(2026, 3, 31), 1) == 2026
    assert academic_year(date(2026, 8, 31), 9) == 2025


def test_numbers_grow_past_two_digits():
    assert format_code("AY{yyyy}-{nn}", 2026, 7) == "AY2026-07"
    assert format_code("AY{yyyy}-{nn}", 2026, 112) == "AY2026-112"
    assert format_code("{nn}/{yyyy}", 2026, 7) == "07/2026"


async def test_codes_count_up_per_academic_year(client, admin_headers):
    codes = []
    for day in ("2026-04-09", "2026-05-01", "2025-12-01", "2026-06-01", "2026-01-15"):
        made = await _create(client, admin_headers, title=day)
        codes.append((await _set(client, made, admin_headers, "release_date", day))["code"])
    assert codes == ["AY2026-01", "AY2026-02", "AY2025-01", "AY2026-03", "AY2025-02"]


async def test_a_date_moved_to_another_year_keeps_its_code(client, admin_headers):
    """D35: the year is then taken from the date, and never from the code."""
    made = await _create(client, admin_headers)
    saved = await _set(client, made, admin_headers, "release_date", "2026-04-09")
    moved = await _set(client, saved, admin_headers, "release_date", "2027-05-01")
    assert moved["code"] == "AY2026-01"
    assert moved["academic_year"] == 2027
    emptied = await _set(client, moved, admin_headers, "release_date", None)
    assert emptied["code"] == "AY2026-01"
    assert emptied["academic_year"] is None
    again = await _set(client, emptied, admin_headers, "release_date", "2028-05-01")
    assert again["code"] == "AY2026-01"


async def test_the_next_number_is_above_the_highest_so_a_gap_is_never_filled(client, admin_headers):
    """Imported codes can have gaps, and a code once used must not come back."""
    institution = await _institution()
    await _add(
        Release(institution_id=institution.id, title="Imported", code="AY2025-42"),
        Release(institution_id=institution.id, title="Imported", code="AY2025-07"),
        Release(institution_id=institution.id, title="Other year", code="AY2024-90"),
        Release(institution_id=institution.id, title="Other form", code="OLD-2025-99"),
    )
    made = await _create(client, admin_headers)
    assert (await _set(client, made, admin_headers, "release_date", "2025-06-01"))[
        "code"
    ] == "AY2025-43"


async def test_a_removed_release_keeps_its_number_taken(client, admin_headers):
    first = await _create(client, admin_headers)
    await _set(client, first, admin_headers, "release_date", "2026-05-01")
    await client.delete(f"{URL}/{first['id']}", headers=admin_headers)
    second = await _create(client, admin_headers)
    assert (await _set(client, second, admin_headers, "release_date", "2026-05-02"))[
        "code"
    ] == "AY2026-02"


async def test_a_new_pattern_applies_to_new_codes_only(client, admin_headers):
    first = await _create(client, admin_headers)
    first = await _set(client, first, admin_headers, "release_date", "2026-05-01")
    response = await client.patch(
        "/api/v1/settings/institution",
        headers=admin_headers,
        json={"field": "release_code_pattern", "value": "PR{yyyy}/{nn}", "version": 0},
    )
    assert response.status_code == 200
    second = await _create(client, admin_headers)
    second = await _set(client, second, admin_headers, "release_date", "2026-05-02")
    assert second["code"] == "PR2026/01"
    current = (await client.get(f"{URL}/{first['id']}", headers=admin_headers)).json()
    assert current["code"] == "AY2026-01"


async def test_saves_at_the_same_moment_get_different_codes(client, admin_headers):
    drafts = [await _create(client, admin_headers, title=str(n)) for n in range(6)]
    responses = await asyncio.gather(
        *(_patch(client, draft, admin_headers, "release_date", "2026-05-01") for draft in drafts)
    )
    assert [response.status_code for response in responses] == [200] * 6
    codes = sorted(response.json()["release"]["code"] for response in responses)
    assert codes == [f"AY2026-0{number}" for number in range(1, 7)]


async def test_a_pattern_cannot_make_a_code_too_long_to_store(client, admin_headers):
    response = await client.patch(
        "/api/v1/settings/institution",
        headers=admin_headers,
        json={"field": "release_code_pattern", "value": "A" * 30 + "{yyyy}{nn}", "version": 0},
    )
    assert (response.status_code, response.json()) == (422, {"detail": "invalid_code_pattern"})


# ---------------------------------------------------------------- readings


async def _open_reading(client, headers, key="ea_views.d28", **fields):
    """A release whose reading applies and is due. The link opens EurekAlert views."""
    made = await _create(client, headers)
    made = await _set(client, made, headers, "ea_url", "https://www.eurekalert.org/news-releases/1")
    for field, value in fields.items():
        made = await _set(client, made, headers, field, value)
    return made, _reading(made, key)


@pytest.mark.parametrize(
    ("written", "stored"),
    [
        (1234, 1234),
        ("1234", 1234),
        ("1,234", 1234),
        ("1,234,567", 1234567),
        (" 12 ", 12),
        ("１２３", 123),
        ("１，２３４", 1234),
        (0, 0),
        ("0", 0),
    ],
)
async def test_numbers_as_people_and_pastes_write_them(client, admin_headers, written, stored):
    """R7.5.8. Zero is a value, never a stand-in for unknown (R6.5.1)."""
    _, reading = await _open_reading(client, admin_headers)
    response = await _enter(client, reading, admin_headers, value=written)
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["value"], body["state"], body["source"]) == (stored, "value", "manual")
    assert body["version"] == reading["version"] + 1


@pytest.mark.parametrize(
    ("written", "code"),
    [
        (-1, "field_out_of_range"),
        ("-5", "field_out_of_range"),
        (1e13, "field_out_of_range"),
        ("1000000000000", "field_out_of_range"),
        ("12.5", "whole_number_required"),
        ("1,5", "field_invalid"),
        ("12,34", "field_invalid"),
        ("many", "field_invalid"),
        (True, "field_invalid"),
    ],
)
async def test_a_number_that_does_not_fit_is_explained(client, admin_headers, written, code):
    _, reading = await _open_reading(client, admin_headers)
    response = await _enter(client, reading, admin_headers, value=written)
    assert (response.status_code, response.json()) == (422, {"detail": code})


async def test_a_score_can_have_decimals_and_views_cannot(client, admin_headers):
    made = await _create(client, admin_headers)
    made = await _set(client, made, admin_headers, "doi", DOI)
    reading = _reading(made, "altmetric.d28")
    assert (await _enter(client, reading, admin_headers, value="12.25")).json()["value"] == 12.25


async def test_a_reading_can_be_set_not_applicable_and_a_rule_leaves_it(client, admin_headers):
    made, reading = await _open_reading(client, admin_headers)
    response = await _enter(client, reading, admin_headers, state="not_applicable")
    body = response.json()
    assert (body["value"], body["state"], body["source"]) == (None, "not_applicable", "manual")
    # A later save that the rule reads does not undo a person's choice (P4).
    made = await _set(
        client, made, admin_headers, "ea_url", "https://www.eurekalert.org/news-releases/2"
    )
    assert _reading(made, "ea_views.d28")["state"] == "not_applicable"


async def test_clearing_goes_back_to_what_the_rules_say(client, admin_headers):
    made, reading = await _open_reading(client, admin_headers)
    entered = (await _enter(client, reading, admin_headers, value=5)).json()
    cleared = (await _enter(client, entered, admin_headers, value="  ")).json()
    assert (cleared["value"], cleared["state"], cleared["source"]) == (None, "missing", "auto")

    entered = (await _enter(client, cleared, admin_headers, value=5)).json()
    made = await _set(client, made, admin_headers, "ea_url", None)
    # A number stays even when the rule stops applying, until a person clears it.
    kept = _reading(made, "ea_views.d28")
    assert (kept["value"], kept["state"]) == (5, "value")
    cleared = (await _enter(client, kept, admin_headers, state="missing")).json()
    assert (cleared["state"], cleared["source"]) == ("not_applicable", "auto")
    # And being the rule's own again, it opens when the link comes back.
    made = await _set(
        client, made, admin_headers, "ea_url", "https://www.eurekalert.org/news-releases/3"
    )
    assert _reading(made, "ea_views.d28")["state"] == "missing"


async def test_a_note_saves_without_touching_the_value(client, admin_headers):
    _, reading = await _open_reading(client, admin_headers)
    entered = (await _enter(client, reading, admin_headers, value=5)).json()
    noted = (await _enter(client, entered, admin_headers, note="  From the portal  ")).json()
    assert (noted["value"], noted["state"], noted["note"]) == (5, "value", "From the portal")


async def test_entering_the_same_number_is_not_a_change(client, admin_headers):
    _, reading = await _open_reading(client, admin_headers)
    entered = (await _enter(client, reading, admin_headers, value=5)).json()
    again = (await _enter(client, entered, admin_headers, value="5")).json()
    assert again["version"] == entered["version"]


async def test_two_people_entering_the_same_reading_get_to_choose(client, admin_headers):
    """R3.3.3."""
    _, reading = await _open_reading(client, admin_headers)
    await _enter(client, reading, admin_headers, value=5)
    stale = await _enter(client, reading, admin_headers, value=6)
    assert stale.status_code == 409
    assert stale.json() == {
        "detail": "conflict",
        "field": "value",
        "current_value": 5,
        "current_version": reading["version"] + 1,
        "current_state": "value",
    }


async def test_a_calculated_measure_cannot_be_entered(client, admin_headers):
    async with SessionLocal() as db:
        measure = await db.scalar(select(Measure).where(Measure.key == "pickups_all"))
        measure.is_active = True
        await db.commit()
    made = await _create(client, admin_headers)
    response = await _enter(client, _reading(made, "pickups_all"), admin_headers, value=5)
    assert (response.status_code, response.json()) == (409, {"detail": "measure_locked"})


async def test_an_automatic_measure_can_still_be_entered_by_hand(client, admin_headers):
    """P4: "Manual entry is always possible, also for automated values"."""
    made = await _create(client, admin_headers)
    made = await _set(client, made, admin_headers, "website_url", "https://news.example.org/a")
    response = await _enter(client, _reading(made, "hp_views.d28"), admin_headers, value=99)
    assert (response.json()["value"], response.json()["source"]) == (99, "manual")


async def test_an_entry_records_who_and_when_for_the_audit_trail(client, admin_headers):
    _, reading = await _open_reading(client, admin_headers)
    body = (await _enter(client, reading, admin_headers, value=5)).json()
    assert body["entered_at"] is not None
    async with SessionLocal() as db:
        chief = await db.scalar(select(User.id).where(User.email == "chief@example.org"))
        entry = await db.scalar(
            select(AuditLog).where(AuditLog.entity_id == reading["id"], AuditLog.field == "value")
        )
    assert (entry.new_value, entry.user_id) == (5, chief)


async def test_a_reading_of_a_removed_release_is_out_of_reach(client, admin_headers):
    made, reading = await _open_reading(client, admin_headers)
    await client.delete(f"{URL}/{made['id']}", headers=admin_headers)
    assert (await _enter(client, reading, admin_headers, value=5)).status_code == 404


async def test_rules_run_when_the_inputs_arrive(client, admin_headers):
    made = await _create(client, admin_headers)
    assert _reading(made, "altmetric.d0")["state"] == "not_applicable"
    assert _reading(made, "ea_views.d0")["state"] == "not_applicable"
    made = await _set(client, made, admin_headers, "doi", DOI)
    assert _reading(made, "altmetric.d0")["state"] == "missing"
    made = await _set(client, made, admin_headers, "embargoed", True)
    assert _reading(made, "ea_views.d0")["state"] == "missing"


# ---------------------------------------------------------------- what is due, and when


async def test_a_reading_is_not_yet_due_until_its_day(client, admin_headers):
    """R6.5.1. Days count in the institution's time zone, not in UTC."""
    today = today_in("Asia/Tokyo")
    made, reading = await _open_reading(client, admin_headers)
    assert reading["display_state"] == "not_yet_due"
    assert reading["due_date"] is None

    released_today = await _set(client, made, admin_headers, "release_date", today.isoformat())
    d28 = _reading(released_today, "ea_views.d28")
    assert d28["due_date"] == (today + timedelta(days=28)).isoformat()
    assert (d28["state"], d28["display_state"]) == ("missing", "not_yet_due")

    long_ago = (today - timedelta(days=28)).isoformat()
    saved = await _set(client, released_today, admin_headers, "release_date", long_ago)
    d28 = _reading(saved, "ea_views.d28")
    assert (d28["due_date"], d28["display_state"]) == (today.isoformat(), "missing")


async def test_a_checkpoint_before_the_release_falls_due_before_it(client, admin_headers):
    """R6.5.3: the case from feedback, Altmetric read before the release goes out."""
    checkpoint = (
        await client.post(
            "/api/v1/checkpoints",
            headers=admin_headers,
            json={
                "values": {
                    "label_en": "Three days before",
                    "offset_days": -3,
                    "remind_days_before": 1,
                }
            },
        )
    ).json()
    response = await client.post(
        "/api/v1/measures",
        headers=admin_headers,
        json={
            "metric": "altmetric",
            "checkpoint_id": checkpoint["id"],
            "label_en": "Altmetric, three days before",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["key"] == "altmetric.d-3"

    today = today_in("Asia/Tokyo")
    made = await _create(client, admin_headers)
    made = await _set(client, made, admin_headers, "doi", DOI)
    in_ten_days = today + timedelta(days=10)
    saved = await _set(client, made, admin_headers, "release_date", in_ten_days.isoformat())
    reading = _reading(saved, "altmetric.d-3")
    assert reading["due_date"] == (today + timedelta(days=7)).isoformat()
    assert reading["remind_on"] == (today + timedelta(days=6)).isoformat()
    assert reading["display_state"] == "not_yet_due"

    # With the release two days away, that day has come, though the release has not.
    in_two_days = today + timedelta(days=2)
    saved = await _set(client, saved, admin_headers, "release_date", in_two_days.isoformat())
    reading = _reading(saved, "altmetric.d-3")
    assert reading["due_date"] == (today - timedelta(days=1)).isoformat()
    assert reading["display_state"] == "missing"
    # And it can be entered, which needs no special case.
    entered = await _enter(client, reading, admin_headers, value=4)
    assert entered.json()["value"] == 4


async def test_a_reminder_on_the_day_is_the_due_date(client, admin_headers):
    made, reading = await _open_reading(client, admin_headers, release_date="2026-05-01")
    assert reading["due_date"] == "2026-05-29"
    assert reading["remind_on"] == "2026-05-29"


# ---------------------------------------------------------------- listing


async def test_newest_first_with_drafts_on_top(client, admin_headers):
    older = await _create(client, admin_headers, title="Older")
    await _set(client, older, admin_headers, "release_date", "2026-04-09")
    newer = await _create(client, admin_headers, title="Newer")
    await _set(client, newer, admin_headers, "release_date", "2026-05-09")
    await _create(client, admin_headers, title="Draft")
    page = (await client.get(URL, headers=admin_headers)).json()
    assert [item["title"] for item in page["items"]] == ["Draft", "Newer", "Older"]
    assert page["total"] == 3


async def test_paging(client, admin_headers):
    for title in ("One", "Two", "Three"):
        await _create(client, admin_headers, title=title)
    page = (await client.get(URL, headers=admin_headers, params={"limit": 2})).json()
    assert (len(page["items"]), page["total"]) == (2, 3)
    rest = (await client.get(URL, headers=admin_headers, params={"limit": 2, "offset": 2})).json()
    assert len(rest["items"]) == 1


async def test_mine_is_the_releases_where_i_am_the_writer(client, headers_for):
    """D30."""
    one = await headers_for(UserRole.editor, "one@example.org")
    two = await headers_for(UserRole.editor, "two@example.org")
    await _link_writer("one@example.org", "One")
    await _create(client, one, title="Mine")
    await _create(client, two, title="No writer")

    page = (await client.get(URL, headers=one, params={"view": "mine"})).json()
    assert [item["title"] for item in page["items"]] == ["Mine"]
    assert page["has_writer_entry"] is True
    everything = (await client.get(URL, headers=one, params={"view": "all"})).json()
    assert everything["total"] == 2


async def test_with_no_writer_entry_nothing_is_mine(client, headers_for):
    """Not everything that has no writer, which is what a plain comparison would find."""
    editor = await headers_for(UserRole.editor)
    await _create(client, editor)
    page = (await client.get(URL, headers=editor, params={"view": "mine"})).json()
    assert page["items"] == []
    assert page["has_writer_entry"] is False


async def test_filtering_by_researcher(client, admin_headers):
    institution = await _institution()
    researcher = await _add(Researcher(institution_id=institution.id, name="Test Person"))
    made = await _create(client, admin_headers, title="Theirs")
    await _set(client, made, admin_headers, "researcher_id", str(researcher.id))
    await _create(client, admin_headers, title="Another")
    page = (
        await client.get(URL, headers=admin_headers, params={"researcher_id": str(researcher.id)})
    ).json()
    assert [item["title"] for item in page["items"]] == ["Theirs"]


# ---------------------------------------------------------------- removing and restoring


async def test_removing_hides_a_release_and_undo_brings_it_back(client, admin_headers):
    made = await _create(client, admin_headers)
    made = await _set(client, made, admin_headers, "release_date", "2026-05-01")
    assert (await client.delete(f"{URL}/{made['id']}", headers=admin_headers)).status_code == 204

    assert (await client.get(URL, headers=admin_headers)).json()["items"] == []
    assert (await client.get(f"{URL}/{made['id']}", headers=admin_headers)).status_code == 404
    assert (await _patch(client, made, admin_headers, "notes", "No")).status_code == 404
    assert (await client.delete(f"{URL}/{made['id']}", headers=admin_headers)).status_code == 404

    restored = await client.post(f"{URL}/{made['id']}/restore", headers=admin_headers)
    assert restored.status_code == 200
    assert restored.json()["code"] == "AY2026-01"
    assert (await client.get(URL, headers=admin_headers)).json()["total"] == 1
    again = await client.post(f"{URL}/{made['id']}/restore", headers=admin_headers)
    assert again.status_code == 404


async def test_removing_and_restoring_are_audit_logged(client, admin_headers):
    made = await _create(client, admin_headers)
    await client.delete(f"{URL}/{made['id']}", headers=admin_headers)
    await client.post(f"{URL}/{made['id']}/restore", headers=admin_headers)
    async with SessionLocal() as db:
        entries = list(
            await db.scalars(
                select(AuditLog).where(
                    AuditLog.entity_id == made["id"], AuditLog.field == "deleted_at"
                )
            )
        )
    assert len(entries) == 2
    assert all(entry.user_id is not None for entry in entries)


# ---------------------------------------------------------------- custom fields


async def _custom_field(client, headers, scope="institution", **values):
    response = await client.post(
        "/api/v1/custom-fields",
        headers=headers,
        json={"scope": scope, "label_en": "Extra", "field_type": "integer", **values},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _custom(client, release, key, headers, version=None, **body):
    version = (
        release["field_versions"].get(f"custom_values.{key}", 0) if version is None else version
    )
    return await client.patch(
        f"{URL}/{release['id']}/custom/{key}",
        headers=headers,
        json={"version": version, **body},
    )


async def test_only_its_owner_changes_a_personal_field(client, headers_for):
    """R6.6.2. Everyone sees it."""
    owner = await headers_for(UserRole.editor, "owner@example.org")
    colleague = await headers_for(UserRole.editor, "colleague@example.org")
    admin = await headers_for(UserRole.admin)
    field = await _custom_field(client, owner, scope="personal")
    made = await _create(client, owner)

    saved = await _custom(client, made, field["key"], owner, value="7")
    assert saved.status_code == 200, saved.text
    assert saved.json()["value"] == {"state": "value", "value": 7}
    for other in (colleague, admin):
        refused = await _custom(client, made, field["key"], other, value="8")
        assert (refused.status_code, refused.json()) == (
            403,
            {"detail": "personal_field_read_only"},
        )
        seen = (await client.get(f"{URL}/{made['id']}", headers=other)).json()
        assert seen["custom_values"][field["key"]] == {"state": "value", "value": 7}


async def test_any_editor_fills_an_institution_field(client, headers_for):
    admin = await headers_for(UserRole.admin)
    editor = await headers_for(UserRole.editor)
    field = await _custom_field(client, admin)
    made = await _create(client, editor)
    assert (await _custom(client, made, field["key"], editor, value=3)).status_code == 200


@pytest.mark.parametrize(
    ("field_type", "written", "stored"),
    [
        ("integer", "1,234", 1234),
        ("integer", -5, -5),
        ("number", "1.5", 1.5),
        ("number", "2", 2),
        ("text", "  Short  ", "Short"),
        ("long_text", "Long\nwith lines", "Long\nwith lines"),
        ("date", " 2026-05-01 ", "2026-05-01"),
        ("boolean", True, True),
        ("boolean", False, False),
        ("url", "example.org/a", "https://example.org/a"),
    ],
)
async def test_each_type_takes_what_fits(client, admin_headers, field_type, written, stored):
    field = await _custom_field(client, admin_headers, field_type=field_type)
    made = await _create(client, admin_headers)
    saved = await _custom(client, made, field["key"], admin_headers, value=written)
    assert saved.status_code == 200, saved.text
    assert saved.json()["value"] == {"state": "value", "value": stored}


@pytest.mark.parametrize(
    ("field_type", "written", "code"),
    [
        ("integer", "1.5", "whole_number_required"),
        ("integer", "many", "field_invalid"),
        ("number", "many", "field_invalid"),
        ("date", "someday", "field_invalid"),
        ("boolean", "maybe", "field_invalid"),
        ("url", "not an address", "invalid_url"),
    ],
)
async def test_each_type_refuses_what_does_not(client, admin_headers, field_type, written, code):
    field = await _custom_field(client, admin_headers, field_type=field_type)
    made = await _create(client, admin_headers)
    refused = await _custom(client, made, field["key"], admin_headers, value=written)
    assert (refused.status_code, refused.json()) == (422, {"detail": code})


async def test_choices_come_from_the_field(client, admin_headers):
    options = [{"label_en": "Newspaper"}, {"label_en": "Radio"}]
    single = await _custom_field(
        client, admin_headers, field_type="single_select", options=options, label_en="One"
    )
    several = await _custom_field(
        client, admin_headers, field_type="multi_select", options=options, label_en="Several"
    )
    made = await _create(client, admin_headers)
    bad = await _custom(client, made, single["key"], admin_headers, value="tv")
    assert bad.status_code == 422
    saved = await _custom(client, made, single["key"], admin_headers, value="radio")
    assert saved.json()["value"]["value"] == "radio"
    bad = await _custom(client, made, several["key"], admin_headers, value=["radio", "tv"])
    assert bad.status_code == 422
    saved = await _custom(client, made, several["key"], admin_headers, value=["radio", "newspaper"])
    assert saved.json()["value"]["value"] == ["radio", "newspaper"]


async def test_choices_can_come_from_a_vocabulary(client, admin_headers):
    vocabulary = (
        await client.post(
            "/api/v1/lists/vocabularies",
            headers=admin_headers,
            json={"values": {"name_en": "Media"}},
        )
    ).json()
    item = (
        await client.post(
            f"/api/v1/lists/vocabularies/{vocabulary['id']}/items",
            headers=admin_headers,
            json={"values": {"label_en": "Wire"}},
        )
    ).json()
    field = await _custom_field(
        client, admin_headers, field_type="single_select", vocabulary_id=vocabulary["id"]
    )
    made = await _create(client, admin_headers)
    saved = await _custom(client, made, field["key"], admin_headers, value="wire")
    assert saved.status_code == 200

    # A choice retired later stays on the releases that have it, and is offered no more.
    await client.patch(
        f"/api/v1/lists/vocabulary-items/{item['id']}",
        headers=admin_headers,
        json={"field": "is_active", "value": False, "version": 0},
    )
    same = await _custom(client, saved.json()["release"], field["key"], admin_headers, value="wire")
    assert same.status_code == 200
    other = await _create(client, admin_headers, title="Other")
    assert (
        await _custom(client, other, field["key"], admin_headers, value="wire")
    ).status_code == 422


async def test_a_custom_value_can_be_not_applicable_and_cleared(client, admin_headers):
    field = await _custom_field(client, admin_headers)
    key = field["key"]
    made = await _create(client, admin_headers)
    saved = await _custom(client, made, key, admin_headers, state="not_applicable")
    assert saved.json()["value"] == {"state": "not_applicable"}
    made = saved.json()["release"]
    assert made["custom_values"][key] == {"state": "not_applicable"}
    cleared = await _custom(client, made, key, admin_headers, value=None)
    assert cleared.json()["value"] is None
    assert key not in cleared.json()["release"]["custom_values"]


async def test_custom_values_conflict_per_field(client, admin_headers):
    field = await _custom_field(client, admin_headers)
    made = await _create(client, admin_headers)
    await _custom(client, made, field["key"], admin_headers, value=1)
    stale = await _custom(client, made, field["key"], admin_headers, value=2)
    assert stale.status_code == 409
    assert stale.json()["current_value"] == {"state": "value", "value": 1}
    assert stale.json()["current_version"] == 1
    assert (await _patch(client, made, admin_headers, "notes", "Other field")).status_code == 200


async def test_a_required_custom_field_cannot_be_emptied_but_can_be_not_applicable(
    client, admin_headers
):
    field = await _custom_field(client, admin_headers, required=True)
    key = field["key"]
    made = await _create(client, admin_headers)
    assert made["missing_required"] == [f"custom_values.{key}"]
    saved = (await _custom(client, made, key, admin_headers, value=1)).json()["release"]
    assert saved["missing_required"] == []
    refused = await _custom(client, saved, key, admin_headers, value="")
    assert (refused.status_code, refused.json()) == (422, {"detail": "field_required"})
    assert (
        await _custom(client, saved, key, admin_headers, state="not_applicable")
    ).status_code == 200


async def test_a_retired_or_unknown_field_takes_no_values(client, admin_headers):
    field = await _custom_field(client, admin_headers)
    await client.patch(
        f"/api/v1/custom-fields/{field['id']}",
        headers=admin_headers,
        json={"field": "is_active", "value": False, "version": 0},
    )
    made = await _create(client, admin_headers)
    assert (await _custom(client, made, field["key"], admin_headers, value=1)).status_code == 422
    assert (await _custom(client, made, "nothing", admin_headers, value=1)).status_code == 404


async def test_custom_values_are_audit_logged_per_field(client, admin_headers):
    field = await _custom_field(client, admin_headers)
    made = await _create(client, admin_headers)
    await _custom(client, made, field["key"], admin_headers, value=7)
    async with SessionLocal() as db:
        entry = await db.scalar(
            select(AuditLog).where(
                AuditLog.entity_id == made["id"],
                AuditLog.field == f"custom_values.{field['key']}",
            )
        )
    assert entry.new_value == {"state": "value", "value": 7}


# ---------------------------------------------------------------- Crossref


async def test_a_lookup_answers_and_saves_nothing(client, admin_headers, crossref_answers):
    crossref_answers["works"][DOI] = WORK
    response = await client.post(
        "/api/v1/lookup/doi", headers=admin_headers, json={"doi": f"doi:{DOI}"}
    )
    assert response.status_code == 200
    body = response.json()
    assert (body["doi"], body["status"], body["journal"]) == (DOI, "found", "Journal of Examples")
    assert (await client.get(URL, headers=admin_headers)).json()["total"] == 0


async def test_an_unknown_doi_is_an_answer_and_a_bad_one_is_explained(
    client, admin_headers, crossref_answers
):
    crossref_answers["status"] = 404
    unknown = await client.post("/api/v1/lookup/doi", headers=admin_headers, json={"doi": DOI})
    assert (unknown.status_code, unknown.json()["status"]) == (200, "not_found")
    bad = await client.post("/api/v1/lookup/doi", headers=admin_headers, json={"doi": "nope"})
    assert (bad.status_code, bad.json()) == (422, {"detail": "invalid_doi"})


async def test_requests_name_the_office_address_from_settings(
    client, admin_headers, crossref_answers
):
    """Crossref's etiquette, with the institution's contact and never a person's."""
    crossref_answers["works"][DOI] = WORK
    await client.post("/api/v1/lookup/doi", headers=admin_headers, json={"doi": DOI})
    agent = crossref_answers["requests"][-1].headers["user-agent"]
    assert agent.startswith("ReleaseRadar/")
    assert "mailto" not in agent

    await client.patch(
        "/api/v1/settings/institution",
        headers=admin_headers,
        json={"field": "contact_email", "value": "office@example.org", "version": 0},
    )
    await client.post("/api/v1/lookup/doi", headers=admin_headers, json={"doi": DOI})
    agent = crossref_answers["requests"][-1].headers["user-agent"]
    assert "mailto:office@example.org" in agent
    assert "chief@example.org" not in agent


async def test_a_doi_is_quoted_for_the_address(client, admin_headers, crossref_answers):
    odd = "10.1002/(sici)1096-8644(199601)99:1<1::aid-ajpa1>3.0.co;2-1"
    crossref_answers["works"][odd] = WORK
    response = await client.post("/api/v1/lookup/doi", headers=admin_headers, json={"doi": odd})
    assert response.json()["status"] == "found"


async def test_the_refetch_button_overwrites_and_says_so(client, admin_headers, crossref_answers):
    made = await _create(client, admin_headers)
    made = await _set(client, made, admin_headers, "doi", DOI)
    made = await _set(client, made, admin_headers, "journal", "Typed by hand")
    crossref_answers["works"][DOI] = WORK
    response = await client.post(f"{URL}/{made['id']}/crossref", headers=admin_headers, json={})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "found"
    assert body["release"]["journal"] == "Journal of Examples"
    assert body["release"]["paper_title"] == "A synthetic paper & its results"
    # A stale screen is told, field by field.
    assert body["release"]["field_versions"]["journal"] == 2
    stale = await _patch(client, made, admin_headers, "journal", "Old screen", 1)
    assert stale.status_code == 409


async def test_filling_gaps_leaves_what_someone_typed(client, admin_headers, crossref_answers):
    made = await _create(client, admin_headers)
    made = await _set(client, made, admin_headers, "doi", DOI)
    made = await _set(client, made, admin_headers, "journal", "Typed by hand")
    crossref_answers["works"][DOI] = WORK
    response = await client.post(
        f"{URL}/{made['id']}/crossref", headers=admin_headers, json={"overwrite": False}
    )
    release = response.json()["release"]
    assert release["journal"] == "Typed by hand"
    assert release["paper_title"] == "A synthetic paper & its results"


async def test_a_refetch_never_empties_a_field(client, admin_headers, crossref_answers):
    made = await _create(client, admin_headers)
    made = await _set(client, made, admin_headers, "doi", DOI)
    made = await _set(client, made, admin_headers, "journal", "Typed by hand")
    crossref_answers["works"][DOI] = {"title": ["Only a title"]}
    response = await client.post(f"{URL}/{made['id']}/crossref", headers=admin_headers, json={})
    release = response.json()["release"]
    assert release["journal"] == "Typed by hand"
    assert release["paper_title"] == "Only a title"


async def test_a_failed_refetch_changes_nothing_and_says_so(
    client, admin_headers, crossref_answers
):
    made = await _create(client, admin_headers)
    made = await _set(client, made, admin_headers, "doi", DOI)
    made = await _set(client, made, admin_headers, "journal", "Typed by hand")
    response = await client.post(f"{URL}/{made['id']}/crossref", headers=admin_headers, json={})
    assert response.json()["status"] == "unavailable"
    assert response.json()["release"]["journal"] == "Typed by hand"


async def test_a_refetch_needs_a_doi(client, admin_headers):
    made = await _create(client, admin_headers)
    response = await client.post(f"{URL}/{made['id']}/crossref", headers=admin_headers, json={})
    assert (response.status_code, response.json()) == (422, {"detail": "invalid_doi"})


@pytest.mark.parametrize(
    ("work", "expected"),
    [
        ({"published": {"date-parts": [[2026, 3, 9]]}}, date(2026, 3, 9)),
        # A year and month is no date to compare with, so nothing is made up.
        ({"published": {"date-parts": [[2026, 3]]}}, None),
        ({"published": {"date-parts": [[None]]}}, None),
        ({}, None),
        # A full date elsewhere is better than a partial one first.
        (
            {
                "published": {"date-parts": [[2026, 3]]},
                "published-online": {"date-parts": [[2026, 3, 2]]},
            },
            date(2026, 3, 2),
        ),
        ({"issued": {"date-parts": [[2026, 13, 40]]}}, None),
    ],
)
def test_a_publication_date_is_a_full_date_or_none(work, expected):
    assert crossref.parse_work(work).publication_date == expected


def test_a_work_with_almost_nothing_still_parses():
    paper = crossref.parse_work({"title": [], "container-title": None, "author": None})
    assert paper == crossref.Paper()


async def test_an_answer_that_is_not_json_counts_as_unavailable(monkeypatch):
    transport = httpx.MockTransport(lambda _: httpx.Response(200, text="<html>Busy</html>"))
    monkeypatch.setattr(crossref, "_transport", transport)
    assert (await crossref.lookup(DOI, None)).status == crossref.UNAVAILABLE


async def test_a_timeout_counts_as_unavailable(monkeypatch):
    def fail(request):
        raise httpx.ConnectTimeout("too slow", request=request)

    monkeypatch.setattr(crossref, "_transport", httpx.MockTransport(fail))
    assert (await crossref.lookup(DOI, None)).status == crossref.UNAVAILABLE


# ---------------------------------------------------------------- history


async def test_history_shows_who_changed_what_newest_first(client, headers_for):
    """R3.4.4."""
    editor = await headers_for(UserRole.editor, "writer@example.org")
    made, reading = await _open_reading(client, editor, notes="First")
    await _enter(client, reading, editor, value=5, note="From the portal")

    history = (await client.get(f"{URL}/{made['id']}/history", headers=editor)).json()
    assert history[-1]["action"] == "create"
    seen = [(entry["entity"], entry["measure_key"], entry["field"]) for entry in history]
    assert ("release", None, "notes") in seen
    assert ("release", None, "ea_url") in seen
    assert ("reading", "ea_views.d28", "value") in seen
    assert ("reading", "ea_views.d28", "note") in seen
    value = next(entry for entry in history if entry["field"] == "value")
    assert (value["old_value"], value["new_value"]) == (None, 5)
    assert value["user_name"] == "writer@example.org"
    assert value["user_active"] is True
    # Readings being set up is not something to read about.
    assert not any(
        entry["entity"] == "reading" and entry["action"] == "create" for entry in history
    )
    # What only supports a reading stays out.
    assert not {entry["field"] for entry in history} & {"version", "entered_at", "source"}
    times = [entry["at"] for entry in history]
    assert times == sorted(times, reverse=True)


async def test_history_marks_a_person_who_has_left(client, headers_for):
    """R3.4.1: their name stays, as a former user."""
    editor = await headers_for(UserRole.editor, "leaver@example.org")
    admin = await headers_for(UserRole.admin)
    made = await _create(client, editor)
    await _set(client, made, editor, "notes", "By someone leaving")
    async with SessionLocal() as db:
        leaver = await db.scalar(select(User).where(User.email == "leaver@example.org"))
        leaver.is_active = False
        await db.commit()
    history = (await client.get(f"{URL}/{made['id']}/history", headers=admin)).json()
    notes = next(entry for entry in history if entry["field"] == "notes")
    assert (notes["user_name"], notes["user_active"]) == ("leaver@example.org", False)


async def test_a_full_export_includes_what_step_1_4_stores(client, admin_headers):
    made = await _create(client, admin_headers)
    await _set(client, made, admin_headers, "release_date", "2026-05-01")
    response = await client.get("/api/v1/settings/export", headers=admin_headers)
    release = next(row for row in response.json()["releases"] if row["id"] == made["id"])
    assert release["code"] == "AY2026-01"


async def test_the_checkpoints_keep_their_check_on_reminders():
    """The database itself refuses anything but the day or the day before."""
    institution = await _institution()
    async with SessionLocal() as db:
        db.add(
            Checkpoint(
                institution_id=institution.id,
                key="d5",
                label_en="Five",
                offset_days=5,
                remind_days_before=3,
            )
        )
        with pytest.raises(Exception, match="remind_days_before_known"):
            await db.commit()


# ---------------------------------------------------------------- what is due


DUE = f"{URL}/due"


async def _writer_with_release(client, headers, email, release_date, **fields):
    """A writer's release whose day-28 EurekAlert views apply, dated as asked."""
    made = await _create(client, headers)
    made = await _set(client, made, headers, "ea_url", "https://www.eurekalert.org/news-releases/1")
    made = await _set(client, made, headers, "release_date", release_date.isoformat())
    for field, value in fields.items():
        made = await _set(client, made, headers, field, value)
    return made


async def test_what_is_due_is_what_the_writer_has_left_to_enter(client, headers_for):
    """R7.5.1, with the release 28 days old, so day 28 is today."""
    editor = await headers_for(UserRole.editor, "writer@example.org")
    await _link_writer("writer@example.org")
    today = today_in("Asia/Tokyo")
    made = await _writer_with_release(
        client, editor, "writer@example.org", today - timedelta(days=28)
    )

    items = (await client.get(DUE, headers=editor)).json()
    assert len(items) == 1
    item = items[0]
    assert item["kind"] == "reading"
    assert item["measure_key"] == "ea_views.d28"
    assert item["release_id"] == made["id"]
    assert item["release_code"] == made["code"]
    assert item["release_title"] == "A release"
    assert item["due_date"] == today.isoformat()
    assert item["due_now"] is True
    assert item["reading_id"] == _reading(made, "ea_views.d28")["id"]
    assert item["version"] == _reading(made, "ea_views.d28")["version"]
    # Nothing here judges: there is no notion of late (P5).
    assert not {"late", "overdue"} & set(item)


async def test_entering_it_or_setting_it_na_clears_it(client, headers_for):
    editor = await headers_for(UserRole.editor, "writer@example.org")
    await _link_writer("writer@example.org")
    today = today_in("Asia/Tokyo")
    first = await _writer_with_release(
        client, editor, "writer@example.org", today - timedelta(days=30)
    )
    second = await _writer_with_release(
        client, editor, "writer@example.org", today - timedelta(days=31)
    )
    assert len((await client.get(DUE, headers=editor)).json()) == 2
    await _enter(client, _reading(first, "ea_views.d28"), editor, value=5)
    assert len((await client.get(DUE, headers=editor)).json()) == 1
    await _enter(client, _reading(second, "ea_views.d28"), editor, state="not_applicable")
    assert (await client.get(DUE, headers=editor)).json() == []


async def test_due_soon_is_included_and_marked_and_further_off_is_not(client, headers_for):
    editor = await headers_for(UserRole.editor, "writer@example.org")
    await _link_writer("writer@example.org")
    today = today_in("Asia/Tokyo")
    # Falling due today, in 3 days, in 4 days.
    for days_ago in (28, 25, 24):
        await _writer_with_release(
            client, editor, "writer@example.org", today - timedelta(days=days_ago)
        )
    items = (await client.get(DUE, headers=editor)).json()
    assert [(item["due_date"], item["due_now"]) for item in items] == [
        (today.isoformat(), True),
        ((today + timedelta(days=3)).isoformat(), False),
    ]


async def test_soonest_comes_first(client, headers_for):
    editor = await headers_for(UserRole.editor, "writer@example.org")
    await _link_writer("writer@example.org")
    today = today_in("Asia/Tokyo")
    for days_ago in (30, 40, 35):
        await _writer_with_release(
            client, editor, "writer@example.org", today - timedelta(days=days_ago)
        )
    items = (await client.get(DUE, headers=editor)).json()
    dates = [item["due_date"] for item in items]
    assert dates == sorted(dates)


async def test_changing_the_writer_moves_the_due_items(client, headers_for):
    """R7.5.2."""
    one = await headers_for(UserRole.editor, "one@example.org")
    two = await headers_for(UserRole.editor, "two@example.org")
    await _link_writer("one@example.org", "One")
    second = await _link_writer("two@example.org", "Two")
    today = today_in("Asia/Tokyo")
    made = await _writer_with_release(client, one, "one@example.org", today - timedelta(days=30))
    assert len((await client.get(DUE, headers=one)).json()) == 1
    assert (await client.get(DUE, headers=two)).json() == []
    await _set(client, made, one, "writer_id", str(second.id))
    assert (await client.get(DUE, headers=one)).json() == []
    assert len((await client.get(DUE, headers=two)).json()) == 1


async def test_a_checkpoint_before_the_release_can_be_due_before_it(client, headers_for):
    """R6.5.3."""
    admin = await headers_for(UserRole.admin, "writer@example.org")
    await _link_writer("writer@example.org")
    checkpoint = (
        await client.post(
            "/api/v1/checkpoints",
            headers=admin,
            json={"values": {"label_en": "Before", "offset_days": -3}},
        )
    ).json()
    await client.post(
        "/api/v1/measures",
        headers=admin,
        json={"metric": "altmetric", "checkpoint_id": checkpoint["id"], "label_en": "Before"},
    )
    today = today_in("Asia/Tokyo")
    made = await _create(client, admin)
    made = await _set(client, made, admin, "doi", DOI)
    await _set(client, made, admin, "release_date", (today + timedelta(days=3)).isoformat())
    items = (await client.get(DUE, headers=admin)).json()
    early = next(item for item in items if item["measure_key"] == "altmetric.d-3")
    assert (early["due_date"], early["due_now"]) == (today.isoformat(), True)


async def test_automatic_measures_ask_nobody(client, headers_for):
    editor = await headers_for(UserRole.editor, "writer@example.org")
    await _link_writer("writer@example.org")
    today = today_in("Asia/Tokyo")
    made = await _create(client, editor)
    made = await _set(client, made, editor, "website_url", "https://news.example.org/a")
    made = await _set(
        client, made, editor, "release_date", (today - timedelta(days=30)).isoformat()
    )
    assert _reading(made, "hp_views.d28")["display_state"] == "missing"
    assert (await client.get(DUE, headers=editor)).json() == []


async def test_a_removed_release_or_someone_elses_is_not_asked_for(client, headers_for):
    editor = await headers_for(UserRole.editor, "writer@example.org")
    other = await headers_for(UserRole.editor, "other@example.org")
    await _link_writer("writer@example.org", "Mine")
    today = today_in("Asia/Tokyo")
    made = await _writer_with_release(
        client, editor, "writer@example.org", today - timedelta(days=30)
    )
    await _writer_with_release(client, other, "other@example.org", today - timedelta(days=30))
    assert len((await client.get(DUE, headers=editor)).json()) == 1
    await client.delete(f"{URL}/{made['id']}", headers=editor)
    assert (await client.get(DUE, headers=editor)).json() == []


async def test_a_viewer_or_someone_with_no_writer_entry_is_asked_for_nothing(client, headers_for):
    editor = await headers_for(UserRole.editor)
    viewer = await headers_for(UserRole.viewer)
    today = today_in("Asia/Tokyo")
    await _writer_with_release(client, editor, "", today - timedelta(days=30))
    assert (await client.get(DUE, headers=editor)).json() == []
    assert (await client.get(DUE, headers=viewer)).json() == []


async def _due_field(client, headers, scope="personal", **values):
    checkpoints = (await client.get("/api/v1/checkpoints", headers=headers)).json()
    d0 = next(row for row in checkpoints if row["key"] == "d0")
    return await _custom_field(
        client, headers, scope=scope, due_checkpoint_id=d0["id"], label_en="Clicks", **values
    )


async def test_a_personal_field_asks_its_owner_on_any_release(client, headers_for):
    """R7.5.1: "or, for personal fields, the owner"."""
    owner = await headers_for(UserRole.editor, "owner@example.org")
    writer = await headers_for(UserRole.editor, "writer@example.org")
    await _link_writer("writer@example.org")
    field = await _due_field(client, owner)
    today = today_in("Asia/Tokyo")
    made = await _create(client, writer)
    made = await _set(client, made, writer, "release_date", today.isoformat())

    items = (await client.get(DUE, headers=owner)).json()
    assert [(item["kind"], item["field_key"], item["field_type"]) for item in items] == [
        ("custom", field["key"], "integer")
    ]
    assert items[0]["release_id"] == made["id"]
    assert items[0]["label_en"] == "Clicks"
    assert items[0]["version"] == 0
    assert (await client.get(DUE, headers=writer)).json() == []

    await _custom(client, made, field["key"], owner, value=3)
    assert (await client.get(DUE, headers=owner)).json() == []


async def test_na_counts_as_an_answer_for_a_custom_field(client, headers_for):
    owner = await headers_for(UserRole.editor, "owner@example.org")
    field = await _due_field(client, owner)
    made = await _create(client, owner)
    made = await _set(client, made, owner, "release_date", today_in("Asia/Tokyo").isoformat())
    await _custom(client, made, field["key"], owner, state="not_applicable")
    assert (await client.get(DUE, headers=owner)).json() == []


async def test_an_institution_field_asks_the_writer(client, headers_for):
    admin = await headers_for(UserRole.admin)
    writer = await headers_for(UserRole.editor, "writer@example.org")
    other = await headers_for(UserRole.editor, "other@example.org")
    await _link_writer("writer@example.org")
    await _due_field(client, admin, scope="institution")
    made = await _create(client, writer)
    await _set(client, made, writer, "release_date", today_in("Asia/Tokyo").isoformat())
    assert len((await client.get(DUE, headers=writer)).json()) == 1
    assert (await client.get(DUE, headers=other)).json() == []
    assert (await client.get(DUE, headers=admin)).json() == []


async def test_a_field_does_not_ask_for_dates_before_it_existed(client, headers_for):
    """Otherwise a new field would ask for every old release at once."""
    owner = await headers_for(UserRole.editor, "owner@example.org")
    await _due_field(client, owner)
    made = await _create(client, owner)
    last_year = today_in("Asia/Tokyo") - timedelta(days=365)
    await _set(client, made, owner, "release_date", last_year.isoformat())
    assert (await client.get(DUE, headers=owner)).json() == []


async def test_a_retired_field_asks_nobody(client, headers_for):
    owner = await headers_for(UserRole.editor, "owner@example.org")
    field = await _due_field(client, owner)
    made = await _create(client, owner)
    await _set(client, made, owner, "release_date", today_in("Asia/Tokyo").isoformat())
    await client.patch(
        f"/api/v1/custom-fields/{field['id']}",
        headers=owner,
        json={"field": "is_active", "value": False, "version": 0},
    )
    assert (await client.get(DUE, headers=owner)).json() == []


async def test_history_names_the_researcher(client, admin_headers):
    institution = await _institution()
    one = await _add(Researcher(institution_id=institution.id, name="First Person"))
    two = await _add(Researcher(institution_id=institution.id, name="Second Person"))
    made = await _create(client, admin_headers)
    made = await _set(client, made, admin_headers, "researcher_id", str(one.id))
    await _set(client, made, admin_headers, "researcher_id", str(two.id))
    history = (await client.get(f"{URL}/{made['id']}/history", headers=admin_headers)).json()
    changes = [entry for entry in history if entry["field"] == "researcher_id"]
    assert [(entry["old_label"], entry["new_label"]) for entry in changes] == [
        ("First Person", "Second Person"),
        (None, "First Person"),
    ]
