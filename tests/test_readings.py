"""Applicability rules and value states (BRIEF section 6.5). All data is synthetic."""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Institution, Measure, Reading, Release
from app.services.readings import display_state, due_date, today_in

# In the order of the built-in measures that are active.
ACTIVE_MEASURES = {"ea_views.d0", "ea_views.d28", "altmetric.d0", "altmetric.d28", "hp_views.d28"}
FULL_RELEASE = {
    "title": "A complete release",
    "doi": "10.1234/example",
    "embargoed": True,
    "release_date": date(2026, 4, 1),
    "ea_url": "https://www.eurekalert.org/news-releases/1000001",
    "website_url": "https://news.example.org/research/1",
}


async def _institution_id():
    async with SessionLocal() as db:
        return await db.scalar(select(Institution.id))


async def _create(**values) -> Release:
    async with SessionLocal() as db:
        release = Release(institution_id=await _institution_id(), **values)
        db.add(release)
        await db.commit()
        return release


async def _change(release: Release, **values) -> None:
    async with SessionLocal() as db:
        stored = await db.get(Release, release.id)
        for name, value in values.items():
            setattr(stored, name, value)
        await db.commit()


async def _readings(release: Release) -> dict[str, Reading]:
    async with SessionLocal() as db:
        rows = await db.execute(
            select(Measure.key, Reading)
            .join(Measure, Measure.id == Reading.measure_id)
            .where(Reading.release_id == release.id)
        )
        return {key: reading for key, reading in rows.all()}


async def _states(release: Release) -> dict[str, str]:
    return {key: reading.state for key, reading in (await _readings(release)).items()}


async def _set_reading(release: Release, key: str, **values) -> None:
    reading = (await _readings(release))[key]
    async with SessionLocal() as db:
        stored = await db.get(Reading, reading.id)
        for name, value in values.items():
            setattr(stored, name, value)
        await db.commit()


# ---------------------------------------------------------------- on creation


async def test_a_draft_has_a_reading_per_active_measure_and_none_of_them_applies_yet():
    states = await _states(await _create(title="Just a title"))
    assert states == dict.fromkeys(ACTIVE_MEASURES, "not_applicable")


async def test_a_complete_release_has_every_measure_applying():
    assert await _states(await _create(**FULL_RELEASE)) == dict.fromkeys(ACTIVE_MEASURES, "missing")


async def test_measures_that_are_not_active_get_no_reading():
    """Pickups stay out until Phase 4 turns them on (R10.10)."""
    readings = await _readings(await _create(**FULL_RELEASE))
    assert "pickups_all" not in readings
    assert "pickups_major" not in readings


async def test_automatic_not_applicable_is_marked_as_coming_from_a_rule():
    readings = await _readings(await _create(title="Just a title"))
    assert {reading.source for reading in readings.values()} == {"auto"}
    assert {reading.entered_by_id for reading in readings.values()} == {None}


# ---------------------------------------------------------------- each rule


@pytest.mark.parametrize(
    ("change", "measures"),
    [
        ({"embargoed": True}, {"ea_views.d0"}),
        ({"doi": "10.1234/example"}, {"altmetric.d0", "altmetric.d28"}),
        ({"ea_url": "https://www.eurekalert.org/news-releases/1"}, {"ea_views.d28"}),
        ({"website_url": "https://news.example.org/a"}, {"hp_views.d28"}),
    ],
    ids=["embargoed", "doi", "eurekalert url", "website url"],
)
async def test_each_rule_opens_its_measures_on_save_and_closes_them_again(change, measures):
    release = await _create(title="Starts empty")

    await _change(release, **change)
    states = await _states(release)
    assert {key for key, state in states.items() if state == "missing"} == measures

    await _change(release, **dict.fromkeys(change, False if "embargoed" in change else None))
    assert await _states(release) == dict.fromkeys(ACTIVE_MEASURES, "not_applicable")


@pytest.mark.parametrize(
    ("url", "applies"),
    [
        ("https://news.example.org/research/1", True),
        ("http://news.example.org", True),
        ("  https://NEWS.example.org/x  ", True),
        ("news.example.org/research/1", True),
        ("https://www.example.org/news/1", False),
        ("https://example.org/news/1", False),
        ("https://news.example.org.evil.test/1", False),
        ("https://sub.news.example.org/1", False),
        ("not a url at all", False),
        ("   ", False),
    ],
)
async def test_website_views_apply_only_on_exactly_the_institution_host(url, applies):
    """A sibling such as an older site must not count (D23, R7.5.8)."""
    release = await _create(title="A release", website_url=url)
    expected = "missing" if applies else "not_applicable"
    assert (await _states(release))["hp_views.d28"] == expected


async def test_website_views_never_apply_while_no_domain_is_configured():
    async with SessionLocal() as db:
        institution = await db.scalar(select(Institution))
        institution.website_domain = None
        await db.commit()
    release = await _create(title="A release", website_url="https://news.example.org/1")
    assert (await _states(release))["hp_views.d28"] == "not_applicable"


async def test_blank_text_counts_as_absent():
    release = await _create(title="A release", doi="   ", ea_url="\t")
    states = await _states(release)
    assert states["altmetric.d28"] == "not_applicable"
    assert states["ea_views.d28"] == "not_applicable"


# ---------------------------------------------------------------- collected-from dates


async def _collect_from(key: str, when: date) -> None:
    async with SessionLocal() as db:
        measure = await db.scalar(select(Measure).where(Measure.key == key))
        measure.collected_from = when
        await db.commit()


@pytest.mark.parametrize(
    ("release_date", "expected"),
    [
        (date(2026, 3, 31), "not_applicable"),
        (date(2026, 4, 1), "missing"),
        (date(2026, 4, 2), "missing"),
    ],
)
async def test_a_release_before_the_collected_from_date_is_not_applicable(release_date, expected):
    """R6.7.1."""
    await _collect_from("altmetric.d28", date(2026, 4, 1))
    release = await _create(title="A", doi="10.1234/x", release_date=release_date)
    assert (await _states(release))["altmetric.d28"] == expected


async def test_moving_the_release_date_across_the_collected_from_date_moves_the_state():
    await _collect_from("altmetric.d28", date(2026, 4, 1))
    release = await _create(title="A", doi="10.1234/x", release_date=date(2026, 5, 1))
    assert (await _states(release))["altmetric.d28"] == "missing"
    await _change(release, release_date=date(2026, 1, 1))
    assert (await _states(release))["altmetric.d28"] == "not_applicable"
    await _change(release, release_date=date(2026, 6, 1))
    assert (await _states(release))["altmetric.d28"] == "missing"


async def test_without_a_release_date_the_collected_from_date_has_no_say():
    await _collect_from("altmetric.d28", date(2026, 4, 1))
    release = await _create(title="A", doi="10.1234/x")
    assert (await _states(release))["altmetric.d28"] == "missing"


# ---------------------------------------------------------------- rules never override people


async def test_a_recorded_number_survives_when_the_rule_stops_applying():
    release = await _create(**FULL_RELEASE)
    await _set_reading(release, "altmetric.d28", state="value", value=42, source="manual")

    await _change(release, doi=None)

    reading = (await _readings(release))["altmetric.d28"]
    assert reading.state == "value"
    assert reading.value == 42
    assert (await _states(release))["altmetric.d0"] == "not_applicable"


async def test_a_not_applicable_set_by_a_person_stays_when_the_rule_starts_applying():
    release = await _create(title="A release")
    await _set_reading(release, "altmetric.d28", state="not_applicable", source="manual")

    await _change(release, doi="10.1234/example")

    states = await _states(release)
    assert states["altmetric.d28"] == "not_applicable"
    assert states["altmetric.d0"] == "missing"


async def test_a_flip_raises_the_version_so_a_stale_edit_is_noticed():
    release = await _create(title="A release")
    before = (await _readings(release))["altmetric.d28"].version
    await _change(release, doi="10.1234/example")
    assert (await _readings(release))["altmetric.d28"].version == before + 1


async def test_saving_an_unrelated_field_leaves_readings_alone():
    release = await _create(**FULL_RELEASE)
    before = {key: reading.version for key, reading in (await _readings(release)).items()}
    await _change(release, notes="Nothing a rule depends on", title="New title")
    after = {key: reading.version for key, reading in (await _readings(release)).items()}
    assert after == before


async def test_a_measure_turned_on_later_gets_its_reading_at_the_next_rule_input_change():
    release = await _create(**FULL_RELEASE)
    async with SessionLocal() as db:
        measure = await db.scalar(select(Measure).where(Measure.key == "pickups_all"))
        measure.is_active = True
        await db.commit()
    await _change(release, release_date=date(2026, 4, 2))
    assert (await _states(release))["pickups_all"] == "missing"


# ---------------------------------------------------------------- computed states


@pytest.mark.parametrize(
    ("state", "due", "expected"),
    [
        ("missing", date(2026, 4, 2), "not_yet_due"),
        ("missing", date(2026, 4, 1), "missing"),
        ("missing", date(2026, 3, 1), "missing"),
        ("missing", None, "not_yet_due"),
        ("value", date(2026, 4, 2), "value"),
        ("value", None, "value"),
        ("not_applicable", date(2026, 4, 2), "not_applicable"),
        ("not_applicable", None, "not_applicable"),
    ],
)
def test_not_yet_due_is_computed_from_the_checkpoint_date(state, due, expected):
    """R6.5.1. A reading due today counts as reached."""
    assert display_state(state, due, today=date(2026, 4, 1)) == expected


def test_due_dates_come_from_the_release_date_and_offset():
    assert due_date(date(2026, 4, 1), 0) == date(2026, 4, 1)
    assert due_date(date(2026, 4, 1), 28) == date(2026, 4, 29)
    assert due_date(None, 28) is None
    assert due_date(date(2026, 4, 1), None) is None


def test_today_means_today_at_the_institution():
    """Late evening UTC is already the next day in Japan."""
    moment = datetime(2026, 4, 1, 15, 30, tzinfo=UTC)
    assert today_in("Asia/Tokyo", moment) == date(2026, 4, 2)
    assert today_in("UTC", moment) == date(2026, 4, 1)


# ---------------------------------------------------------------- inferred day-0 Altmetric


PAPER = {"title": "A paper", "doi": "10.1234/inferred", "release_date": date(2026, 4, 1)}


async def test_a_paper_published_on_or_after_the_release_day_has_an_inferred_zero():
    from decimal import Decimal

    for published in (date(2026, 4, 1), date(2026, 4, 9)):
        readings = await _readings(await _create(**PAPER, publication_date=published))
        day0 = readings["altmetric.d0"]
        assert (day0.state, day0.value, day0.source, day0.inferred) == (
            "value",
            Decimal(0),
            "auto",
            True,
        )
        # Only day 0: by day 28 there is attention to count.
        assert (readings["altmetric.d28"].state, readings["altmetric.d28"].inferred) == (
            "missing",
            False,
        )


@pytest.mark.parametrize(
    ("values", "state"),
    [
        ({"publication_date": date(2026, 3, 31)}, "missing"),
        ({"publication_date": None}, "missing"),
        ({"publication_date": date(2026, 4, 2), "doi": None}, "not_applicable"),
        ({"publication_date": date(2026, 4, 2), "release_date": None}, "missing"),
    ],
)
async def test_no_inferred_zero_when_the_paper_came_first_or_a_date_is_unknown(values, state):
    day0 = (await _readings(await _create(**{**PAPER, **values})))["altmetric.d0"]
    assert (day0.state, day0.inferred) == (state, False)


async def test_the_inferred_zero_follows_the_dates_and_the_doi():
    release = await _create(**PAPER, publication_date=date(2026, 4, 2))
    first = (await _readings(release))["altmetric.d0"]

    await _change(release, publication_date=date(2026, 3, 1))
    moved = (await _readings(release))["altmetric.d0"]
    assert (moved.state, moved.value, moved.inferred) == ("missing", None, False)
    assert moved.version == first.version + 1

    await _change(release, release_date=date(2026, 2, 20))
    assert (await _readings(release))["altmetric.d0"].inferred is True

    await _change(release, doi=None)
    gone = (await _readings(release))["altmetric.d0"]
    assert (gone.state, gone.source, gone.inferred) == ("not_applicable", "auto", False)

    await _change(release, doi="10.1234/back")
    assert (await _readings(release))["altmetric.d0"].inferred is True


async def test_a_typed_number_replaces_it_and_clearing_lets_it_return(client, headers_for):
    from app.models import UserRole

    editor = await headers_for(UserRole.editor)
    release = await _create(**PAPER, publication_date=date(2026, 4, 2))
    day0 = (await _readings(release))["altmetric.d0"]
    url = f"/api/v1/readings/{day0.id}"

    shown = (await client.get(f"/api/v1/releases/{release.id}", headers=editor)).json()
    out = next(r for r in shown["readings"] if r["measure_key"] == "altmetric.d0")
    assert (out["value"], out["display_state"], out["inferred"]) == (0, "value", True)

    typed = await client.patch(url, json={"version": day0.version, "value": "3"}, headers=editor)
    assert typed.json()["inferred"] is False and typed.json()["source"] == "manual"
    cleared = await client.patch(
        url, json={"version": typed.json()["version"], "value": ""}, headers=editor
    )
    assert (cleared.json()["value"], cleared.json()["inferred"]) == (0, True)
    # A typed 0 is a person's 0.
    zero = await client.patch(
        url, json={"version": cleared.json()["version"], "value": "0"}, headers=editor
    )
    assert (zero.json()["source"], zero.json()["inferred"]) == ("manual", False)
    marked = await client.patch(
        url, json={"version": zero.json()["version"], "state": "not_applicable"}, headers=editor
    )
    assert (marked.json()["state"], marked.json()["inferred"]) == ("not_applicable", False)
    # A person's N/A stays, whatever the dates do.
    await _change(release, publication_date=date(2026, 4, 5))
    stays = (await _readings(release))["altmetric.d0"]
    assert (stays.state, stays.source, stays.inferred) == ("not_applicable", "manual", False)
