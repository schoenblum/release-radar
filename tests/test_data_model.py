"""Seeds, constraints and the conventions every table must follow. All data is synthetic."""

import os
import subprocess
import sys
from datetime import date

import pytest
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.bootstrap import bootstrap
from app.database import Base, SessionLocal
from app.models import (
    Checkpoint,
    CoreFieldConfig,
    CustomField,
    Institution,
    Measure,
    Reading,
    Release,
    Researcher,
    ResearchField,
    Unit,
    User,
    UserRole,
    Vocabulary,
    VocabularyItem,
    Writer,
)
from app.seeds import CORE_FIELDS
from app.services.security import hash_password
from tests.conftest import _PARSED_URL, ROOT, admin_connection


async def _institution_id():
    async with SessionLocal() as db:
        return await db.scalar(select(Institution.id))


async def _make_other_institution():
    async with SessionLocal() as db:
        other = Institution(name_en="Other University", timezone="UTC", settings={})
        db.add(other)
        await db.commit()
        return other.id


async def _refused(*objects) -> None:
    """The database must refuse to save these."""
    async with SessionLocal() as db:
        db.add_all(objects)
        with pytest.raises(IntegrityError):
            await db.commit()


# ---------------------------------------------------------------- conventions


def test_every_table_carries_institution_id():
    missing = [
        table.name
        for table in Base.metadata.sorted_tables
        if table.name != "institutions" and "institution_id" not in table.columns
    ]
    assert missing == []


def test_every_foreign_key_to_users_restricts_deletion():
    """R3.4.2: records belong to the institution, so a user can never take data along."""
    keys = [
        (table.name, key.parent.name, key.ondelete)
        for table in Base.metadata.sorted_tables
        for key in table.foreign_keys
        if key.column.table.name == "users"
    ]
    assert keys
    assert [key for key in keys if key[2] != "RESTRICT"] == []


# ---------------------------------------------------------------- seeds


async def test_institution_defaults():
    async with SessionLocal() as db:
        institution = await db.scalar(select(Institution))
    assert institution.website_domain == "news.example.org"
    assert institution.release_code_pattern == "AY{yyyy}-{nn}"
    assert institution.major_outlet_threshold == 1_000_000
    # A new install lands viewers on Analysis (phase-2 brief §4.3).
    assert institution.landing_pages == {"admin": "mine", "editor": "mine", "viewer": "analysis"}
    assert "eurekalert" in institution.ea_url_pattern
    assert institution.contact_email is None


async def test_built_in_checkpoints():
    async with SessionLocal() as db:
        checkpoints = {c.key: c for c in await db.scalars(select(Checkpoint))}
    assert {key: c.offset_days for key, c in checkpoints.items()} == {"d0": 0, "d28": 28}
    assert checkpoints["d0"].label_en == "Release day"
    assert checkpoints["d28"].label_ja == "28 日目"


async def test_built_in_measures_follow_the_brief():
    async with SessionLocal() as db:
        measures = {m.key: m for m in await db.scalars(select(Measure))}
        checkpoints = {c.id: c.key for c in await db.scalars(select(Checkpoint))}
    summary = {
        key: (m.metric, checkpoints.get(m.checkpoint_id), m.source, m.applicability, m.is_active)
        for key, m in measures.items()
    }
    assert summary == {
        "ea_views.d0": ("ea_views", "d0", "manual", "embargoed", True),
        "ea_views.d28": ("ea_views", "d28", "manual", "has_ea_url", True),
        "altmetric.d0": ("altmetric", "d0", "manual", "has_doi", True),
        "altmetric.d28": ("altmetric", "d28", "manual", "has_doi", True),
        "hp_views.d28": ("hp_views", "d28", "ga4", "website_on_domain", True),
        "pickups_all": ("pickups_all", None, "derived", "always", False),
        "pickups_major": ("pickups_major", None, "derived", "always", False),
    }
    assert measures["ea_views.d0"].label_en == "EurekAlert embargoed views"
    assert all(m.label_ja for m in measures.values())


async def test_every_core_field_is_configurable_and_the_japanese_title_starts_hidden():
    async with SessionLocal() as db:
        configs = {c.key: c for c in await db.scalars(select(CoreFieldConfig))}
    assert set(configs) == set(CORE_FIELDS)
    assert [key for key, c in configs.items() if c.hidden] == ["title_ja"]
    assert sorted(c.position for c in configs.values()) == list(range(len(CORE_FIELDS)))


async def test_seeding_repeats_without_duplicating_or_undoing_admin_changes():
    async with SessionLocal() as db:
        d28 = await db.scalar(select(Checkpoint).where(Checkpoint.key == "d28"))
        d28.offset_days = 30
        d28.label_en = "Day 30"
        measure = await db.scalar(select(Measure).where(Measure.key == "ea_views.d28"))
        measure.is_active = False
        config = await db.scalar(select(CoreFieldConfig).where(CoreFieldConfig.key == "title_ja"))
        config.hidden = False
        await db.commit()

    await bootstrap()
    await bootstrap()

    async with SessionLocal() as db:
        assert len(list(await db.scalars(select(Checkpoint)))) == 2
        assert len(list(await db.scalars(select(Measure)))) == 7
        d28 = await db.scalar(select(Checkpoint).where(Checkpoint.key == "d28"))
        assert (d28.offset_days, d28.label_en) == (30, "Day 30")
        measure = await db.scalar(select(Measure).where(Measure.key == "ea_views.d28"))
        assert measure.is_active is False
        config = await db.scalar(select(CoreFieldConfig).where(CoreFieldConfig.key == "title_ja"))
        assert config.hidden is False


async def test_a_missing_seed_is_added_back_to_an_existing_install():
    async with SessionLocal() as db:
        config = await db.scalar(select(CoreFieldConfig).where(CoreFieldConfig.key == "notes"))
        await db.delete(config)
        await db.commit()
    await bootstrap()
    async with SessionLocal() as db:
        assert await db.scalar(select(CoreFieldConfig.id).where(CoreFieldConfig.key == "notes"))


async def test_bootstrap_fills_in_a_website_domain_only_when_there_is_none():
    async with SessionLocal() as db:
        await db.execute(update(Institution).values(website_domain=None))
        await db.commit()
    await bootstrap()
    async with SessionLocal() as db:
        institution = await db.scalar(select(Institution))
        assert institution.website_domain == "news.example.org"
        institution.website_domain = "changed.example.org"
        await db.commit()
    await bootstrap()
    async with SessionLocal() as db:
        assert await db.scalar(select(Institution.website_domain)) == "changed.example.org"


# ---------------------------------------------------------------- releases


async def test_a_release_needs_a_title_or_a_doi():
    """R7.5.6."""
    institution_id = await _institution_id()
    await _refused(Release(institution_id=institution_id))
    async with SessionLocal() as db:
        db.add(Release(institution_id=institution_id, title="Only a title"))
        db.add(Release(institution_id=institution_id, doi="10.1234/only-a-doi"))
        await db.commit()


async def test_release_codes_are_unique_per_institution_but_drafts_may_have_none():
    institution_id = await _institution_id()
    other_id = await _make_other_institution()
    async with SessionLocal() as db:
        db.add(Release(institution_id=institution_id, title="First", code="AY2026-01"))
        db.add(Release(institution_id=other_id, title="Elsewhere", code="AY2026-01"))
        db.add(Release(institution_id=institution_id, title="Draft one"))
        db.add(Release(institution_id=institution_id, title="Draft two"))
        await db.commit()
    await _refused(Release(institution_id=institution_id, title="Second", code="AY2026-01"))


async def test_top_page_position_needs_the_top_page_and_starts_at_one():
    institution_id = await _institution_id()
    await _refused(Release(institution_id=institution_id, title="No", ea_top_position=1))
    await _refused(
        Release(institution_id=institution_id, title="No", ea_top_page=True, ea_top_position=0)
    )
    async with SessionLocal() as db:
        db.add(
            Release(institution_id=institution_id, title="Yes", ea_top_page=True, ea_top_position=1)
        )
        await db.commit()


async def test_a_list_entry_in_use_cannot_be_deleted():
    """Records are retired, not deleted, once releases refer to them."""
    institution_id = await _institution_id()
    async with SessionLocal() as db:
        writer = Writer(institution_id=institution_id, display_name_en="A. Writer")
        researcher = Researcher(institution_id=institution_id, name="R. Searcher")
        db.add_all([writer, researcher])
        await db.flush()
        db.add(
            Release(
                institution_id=institution_id,
                title="In use",
                writer_id=writer.id,
                researcher_id=researcher.id,
            )
        )
        await db.commit()
    for target in (writer, researcher):
        async with SessionLocal() as db:
            await db.delete(await db.get(type(target), target.id))
            with pytest.raises(IntegrityError):
                await db.commit()


async def test_deleting_a_release_takes_its_readings_along():
    institution_id = await _institution_id()
    async with SessionLocal() as db:
        release = Release(institution_id=institution_id, title="Goes away")
        db.add(release)
        await db.commit()
    async with SessionLocal() as db:
        assert list(await db.scalars(select(Reading).where(Reading.release_id == release.id)))
        await db.delete(await db.get(Release, release.id))
        await db.commit()
    async with SessionLocal() as db:
        assert not list(await db.scalars(select(Reading).where(Reading.release_id == release.id)))


# ---------------------------------------------------------------- readings


async def _reading_for_new_release() -> Reading:
    institution_id = await _institution_id()
    async with SessionLocal() as db:
        release = Release(institution_id=institution_id, title="A release")
        db.add(release)
        await db.commit()
        return await db.scalar(select(Reading).where(Reading.release_id == release.id).limit(1))


@pytest.mark.parametrize(
    ("state", "value"),
    [
        ("value", None),
        ("missing", 0),
        ("not_applicable", 0),
        ("missing", 5),
    ],
)
async def test_a_number_and_the_value_state_always_go_together(state, value):
    """Value states: nothing can store a 0 for "unknown"."""
    reading = await _reading_for_new_release()
    async with SessionLocal() as db:
        with pytest.raises(IntegrityError):
            await db.execute(
                update(Reading).where(Reading.id == reading.id).values(state=state, value=value)
            )


async def test_zero_is_a_real_value():
    reading = await _reading_for_new_release()
    async with SessionLocal() as db:
        row = await db.get(Reading, reading.id)
        row.state, row.value = "value", 0
        await db.commit()
    async with SessionLocal() as db:
        assert (await db.get(Reading, reading.id)).value == 0


async def test_one_reading_per_release_and_measure():
    reading = await _reading_for_new_release()
    await _refused(
        Reading(
            institution_id=reading.institution_id,
            release_id=reading.release_id,
            measure_id=reading.measure_id,
        )
    )


async def test_a_value_cannot_be_negative():
    reading = await _reading_for_new_release()
    async with SessionLocal() as db:
        row = await db.get(Reading, reading.id)
        row.state, row.value = "value", -1
        with pytest.raises(IntegrityError):
            await db.commit()


async def test_a_measure_cannot_use_an_unknown_rule():
    await _refused(
        Measure(
            institution_id=await _institution_id(),
            key="made.up",
            metric="made_up",
            source="manual",
            applicability="whenever",
            unit="count",
            label_en="Made up",
        )
    )


async def test_measure_collected_from_is_a_date():
    institution_id = await _institution_id()
    async with SessionLocal() as db:
        measure = await db.scalar(
            select(Measure).where(
                Measure.institution_id == institution_id, Measure.key == "pickups_all"
            )
        )
        measure.collected_from = date(2027, 1, 1)
        await db.commit()
    async with SessionLocal() as db:
        assert (await db.get(Measure, measure.id)).collected_from == date(2027, 1, 1)


# ---------------------------------------------------------------- lists


async def test_lists_keep_names_in_both_languages_and_link_up():
    institution_id = await _institution_id()
    async with SessionLocal() as db:
        field = ResearchField(
            institution_id=institution_id,
            name_en="Sciences",
            name_ja="理系",
            scope_note="Units in the sciences",
        )
        db.add(field)
        await db.flush()
        unit = Unit(
            institution_id=institution_id,
            key="Synthetic School",
            name_en="School of Synthetic Studies",
            name_ja="合成研究科",
            short_label="Synthetic",
            unit_type="school",
            aliases=["SYNTH", "Synth School"],
            default_field_id=field.id,
        )
        db.add(unit)
        await db.commit()
    async with SessionLocal() as db:
        stored = await db.get(Unit, unit.id)
        assert stored.aliases == ["SYNTH", "Synth School"]
        assert stored.default_field_id == field.id
        assert stored.is_active is True


async def test_list_keys_are_unique_per_institution():
    institution_id = await _institution_id()
    async with SessionLocal() as db:
        db.add(Unit(institution_id=institution_id, key="Same", name_en="One"))
        await db.commit()
    await _refused(Unit(institution_id=institution_id, key="Same", name_en="Two"))
    await _refused(Unit(institution_id=institution_id, key="Typed", name_en="X", unit_type="club"))


async def test_a_user_has_at_most_one_writer_entry_and_a_writer_needs_no_user(make_user):
    """R3.2.1: former staff remain as writers without an account."""
    user = await make_user()
    institution_id = user.institution_id
    async with SessionLocal() as db:
        db.add(Writer(institution_id=institution_id, display_name_en="Linked", user_id=user.id))
        db.add(Writer(institution_id=institution_id, display_name_en="Former one"))
        db.add(Writer(institution_id=institution_id, display_name_en="Former two"))
        await db.commit()
    await _refused(Writer(institution_id=institution_id, display_name_en="Again", user_id=user.id))


async def test_vocabulary_items_belong_to_their_list():
    institution_id = await _institution_id()
    async with SessionLocal() as db:
        vocabulary = Vocabulary(institution_id=institution_id, key="channels", name_en="Channels")
        db.add(vocabulary)
        await db.flush()
        db.add(
            VocabularyItem(
                institution_id=institution_id,
                vocabulary_id=vocabulary.id,
                key="press",
                label_en="Press",
                label_ja="報道",
            )
        )
        await db.commit()
    await _refused(
        VocabularyItem(
            institution_id=institution_id,
            vocabulary_id=vocabulary.id,
            key="press",
            label_en="Duplicate",
        )
    )


# ---------------------------------------------------------------- researchers


async def test_researchers_may_share_a_name():
    """R6.3.1: the identity is the ID."""
    institution_id = await _institution_id()
    async with SessionLocal() as db:
        one = Researcher(institution_id=institution_id, name="Test Person")
        two = Researcher(institution_id=institution_id, name="Test Person")
        db.add_all([one, two])
        await db.commit()
    assert one.id != two.id
    assert one.gender == "not_recorded"
    assert one.status == "incomplete"


@pytest.mark.parametrize("values", [{"gender": "unknown"}, {"status": "maybe"}])
async def test_researcher_gender_and_status_come_from_their_lists(values):
    await _refused(Researcher(institution_id=await _institution_id(), name="Test", **values))


# ---------------------------------------------------------------- custom fields


def _custom_field(institution_id, **values) -> CustomField:
    base = {
        "institution_id": institution_id,
        "key": "a_field",
        "label_en": "A field",
        "field_type": "integer",
        "scope": "institution",
    }
    return CustomField(**(base | values))


async def test_valid_custom_fields(make_user):
    user = await make_user()
    institution_id = user.institution_id
    async with SessionLocal() as db:
        checkpoint = await db.scalar(select(Checkpoint).where(Checkpoint.key == "d28"))
        db.add(
            _custom_field(
                institution_id,
                key="institutional",
                required=True,
                score_eligible=True,
                due_checkpoint_id=checkpoint.id,
            )
        )
        db.add(_custom_field(institution_id, key="mine", scope="personal", owner_id=user.id))
        await db.commit()


@pytest.mark.parametrize(
    "values",
    [
        {"scope": "personal"},
        {"owner": True},
        {"scope": "personal", "owner": True, "required": True},
        {"scope": "personal", "owner": True, "score_eligible": True},
        {"field_type": "text", "score_eligible": True},
        {"field_type": "emoji"},
        {"scope": "team"},
    ],
    ids=[
        "personal without owner",
        "institution with owner",
        "personal cannot be required",
        "personal cannot be scored",
        "text cannot be scored",
        "unknown type",
        "unknown scope",
    ],
)
async def test_invalid_custom_fields_are_refused(make_user, values):
    """R6.6.2: personal fields never reach evaluation pages."""
    user = await make_user()
    values = dict(values)
    if values.pop("owner", False):
        values["owner_id"] = user.id
    await _refused(_custom_field(user.institution_id, **values))


async def test_a_user_who_owns_a_personal_field_cannot_be_deleted(make_user):
    user = await make_user()
    async with SessionLocal() as db:
        db.add(_custom_field(user.institution_id, scope="personal", owner_id=user.id))
        await db.commit()
    async with SessionLocal() as db:
        await db.delete(await db.get(User, user.id))
        with pytest.raises(IntegrityError):
            await db.commit()


async def test_custom_values_are_kept_by_field_key():
    institution_id = await _institution_id()
    values = {
        "clicks": {"state": "value", "value": 12},
        "pitched": {"state": "not_applicable"},
    }
    async with SessionLocal() as db:
        release = Release(institution_id=institution_id, title="Custom", custom_values=values)
        db.add(release)
        await db.commit()
    async with SessionLocal() as db:
        assert (await db.get(Release, release.id)).custom_values == values


# ---------------------------------------------------------------- migrations


def _alembic(*arguments: str, database_url: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=ROOT,
        env={**os.environ, "DATABASE_URL": database_url},
        capture_output=True,
        text=True,
    )


def _migrate(*arguments: str, database_url: str) -> None:
    """Run alembic, failing with its error only. Never ``assert _alembic(...)`` inline: pytest
    then prints the call's arguments, and the address holds the database password."""
    result = _alembic(*arguments, database_url=database_url)
    if result.returncode != 0:
        error = result.stderr[-3000:]
        if _PARSED_URL.password:
            error = error.replace(_PARSED_URL.password, "***")
        pytest.fail(f"alembic {' '.join(arguments)} failed:\n{error}", pytrace=False)


async def test_upgrading_an_existing_install_keeps_its_data_and_can_be_reversed():
    """The path a real install takes, from step 1.1 with accounts already in it."""
    name = "release_radar_upgrade_test"
    url = _PARSED_URL.set(database=name).render_as_string(hide_password=False)
    connection = await admin_connection()
    try:
        await connection.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        await connection.execute(f'CREATE DATABASE "{name}"')
    finally:
        await connection.close()

    async def run_sql(statement: str, *arguments):
        import asyncpg

        database = await asyncpg.connect(
            host=_PARSED_URL.host,
            port=_PARSED_URL.port or 5432,
            user=_PARSED_URL.username,
            password=_PARSED_URL.password,
            database=name,
        )
        try:
            return await database.fetchrow(statement, *arguments)
        finally:
            await database.close()

    first = _alembic("upgrade", "0001", database_url=url)
    assert first.returncode == 0, first.stderr
    institution = await run_sql(
        "INSERT INTO institutions (id, name_en, timezone, ay_start_month, settings) "
        "VALUES (gen_random_uuid(), 'Existing', 'Asia/Tokyo', 4, '{}') RETURNING id"
    )
    await run_sql(
        "INSERT INTO users (id, institution_id, email, password_hash, role, is_active, "
        "force_password_change, token_version) VALUES "
        "(gen_random_uuid(), $1, 'kept@example.org', $2, 'admin', true, false, 0)",
        institution["id"],
        hash_password("a-password-from-before"),
    )

    upgraded = _alembic("upgrade", "head", database_url=url)
    assert upgraded.returncode == 0, upgraded.stderr

    row = await run_sql(
        "SELECT name_en, release_code_pattern, major_outlet_threshold, landing_pages, "
        "ea_url_pattern FROM institutions"
    )
    assert row["name_en"] == "Existing"
    assert row["release_code_pattern"] == "AY{yyyy}-{nn}"
    assert row["major_outlet_threshold"] == 1_000_000
    assert "viewer" in row["landing_pages"]
    assert row["ea_url_pattern"].endswith(r"news-releases/\d+$")
    assert (await run_sql("SELECT email FROM users"))["email"] == "kept@example.org"

    reversed_ = _alembic("downgrade", "0001", database_url=url)
    assert reversed_.returncode == 0, reversed_.stderr
    assert (await run_sql("SELECT email FROM users"))["email"] == "kept@example.org"
    assert (await run_sql("SELECT to_regclass('releases') AS t"))["t"] is None

    again = _alembic("upgrade", "head", database_url=url)
    assert again.returncode == 0, again.stderr

    connection = await admin_connection()
    try:
        await connection.execute(f'DROP DATABASE "{name}" WITH (FORCE)')
    finally:
        await connection.close()


async def test_a_bootstrap_user_role_is_stored_by_name():
    async with SessionLocal() as db:
        admin = await db.scalar(select(User).where(User.role == UserRole.admin))
    assert admin.role == UserRole.admin


async def test_the_publication_date_moves_next_to_the_doi_and_nothing_else_moves():
    name = "release_radar_reorder_test"
    url = _PARSED_URL.set(database=name).render_as_string(hide_password=False)
    connection = await admin_connection()
    try:
        await connection.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        await connection.execute(f'CREATE DATABASE "{name}"')
    finally:
        await connection.close()

    import asyncpg

    async def run(statement: str, *arguments):
        database = await asyncpg.connect(
            host=_PARSED_URL.host,
            port=_PARSED_URL.port or 5432,
            user=_PARSED_URL.username,
            password=_PARSED_URL.password,
            database=name,
        )
        try:
            return await database.fetch(statement, *arguments)
        finally:
            await database.close()

    try:
        _migrate("upgrade", "0005", database_url=url)
        institution = (
            await run(
                "INSERT INTO institutions (id, name_en, timezone, ay_start_month, settings) "
                "VALUES (gen_random_uuid(), 'Existing', 'Asia/Tokyo', 4, '{}') RETURNING id"
            )
        )[0]["id"]
        # The old default order, with one field an admin had already moved to the top.
        old = ["notes", "code", "title", "doi", "journal", "paper_title", "publication_date"]
        for position, key in enumerate(old):
            await run(
                "INSERT INTO core_field_configs (id, institution_id, key, hidden, required, "
                "position) VALUES (gen_random_uuid(), $1, $2, false, false, $3)",
                institution,
                key,
                position,
            )
        upgraded = _alembic("upgrade", "0006", database_url=url)
        assert upgraded.returncode == 0, upgraded.stderr
        rows = await run("SELECT key FROM core_field_configs ORDER BY position")
        assert [row["key"] for row in rows] == [
            "notes",
            "code",
            "title",
            "doi",
            "publication_date",
            "journal",
            "paper_title",
        ]
        # 0007 adds the researcher's gender right after the researcher, shown and optional.
        await run(
            "INSERT INTO core_field_configs (id, institution_id, key, hidden, required, "
            "position) VALUES (gen_random_uuid(), $1, 'researcher', false, true, 2)",
            institution,
        )
        _migrate("upgrade", "head", database_url=url)
        rows = await run(
            "SELECT key, hidden, required, position FROM core_field_configs ORDER BY position"
        )
        keys = [row["key"] for row in rows]
        assert keys.index("researcher_gender") == keys.index("researcher") + 1
        assert [row["position"] for row in rows] == list(range(len(rows)))
        gender = next(row for row in rows if row["key"] == "researcher_gender")
        assert (gender["hidden"], gender["required"]) == (False, False)
        # Running it again would add nothing: the row exists.
        _migrate("downgrade", "0006", database_url=url)
        assert "researcher_gender" not in [
            row["key"] for row in await run("SELECT key FROM core_field_configs")
        ]
        _migrate("downgrade", "0005", database_url=url)
    finally:
        connection = await admin_connection()
        try:
            await connection.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        finally:
            await connection.close()


async def test_release_types_arrive_with_every_existing_release_peer_reviewed():
    """0009 seeds the list for an existing install, sets the default, fills in every release
    (removed ones too) and puts the field after the field (STEM/HSS) on forms."""
    name = "release_radar_types_test"
    url = _PARSED_URL.set(database=name).render_as_string(hide_password=False)
    connection = await admin_connection()
    try:
        await connection.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        await connection.execute(f'CREATE DATABASE "{name}"')
    finally:
        await connection.close()

    import asyncpg

    async def run(statement: str, *arguments):
        database = await asyncpg.connect(
            host=_PARSED_URL.host,
            port=_PARSED_URL.port or 5432,
            user=_PARSED_URL.username,
            password=_PARSED_URL.password,
            database=name,
        )
        try:
            return await database.fetch(statement, *arguments)
        finally:
            await database.close()

    try:
        _migrate("upgrade", "0008", database_url=url)
        institution = (
            await run(
                "INSERT INTO institutions (id, name_en, timezone, ay_start_month, settings) "
                "VALUES (gen_random_uuid(), 'Existing', 'Asia/Tokyo', 4, '{}') RETURNING id"
            )
        )[0]["id"]
        for position, key in enumerate(("code", "title", "unit", "field", "doi")):
            await run(
                "INSERT INTO core_field_configs (id, institution_id, key, hidden, required, "
                "position) VALUES (gen_random_uuid(), $1, $2, false, false, $3)",
                institution,
                key,
                position,
            )
        for title, removed in (("Kept", None), ("Removed", date(2026, 1, 1))):
            await run(
                "INSERT INTO releases (id, institution_id, title, authors, embargoed, "
                "ea_top_page, custom_values, field_versions, deleted_at) VALUES "
                "(gen_random_uuid(), $1, $2, '[]', false, false, '{}', '{}', $3)",
                institution,
                title,
                removed,
            )
        upgraded = _alembic("upgrade", "head", database_url=url)
        assert upgraded.returncode == 0, upgraded.stderr
        types = await run("SELECT id, key FROM release_types ORDER BY position")
        assert len(types) == 11
        assert types[0]["key"] == "peer_reviewed"
        default = (await run("SELECT default_release_type_id AS id FROM institutions"))[0]["id"]
        assert default == types[0]["id"]
        assert {row["t"] for row in await run("SELECT release_type_id AS t FROM releases")} == {
            default
        }
        rows = await run("SELECT key, position FROM core_field_configs ORDER BY position")
        assert [row["key"] for row in rows] == [
            "code",
            "title",
            "unit",
            "field",
            "release_type",
            "doi",
        ]
        assert [row["position"] for row in rows] == list(range(len(rows)))
        _migrate("downgrade", "0008", database_url=url)
        assert (await run("SELECT to_regclass('release_types') AS t"))[0]["t"] is None
        assert "release_type" not in [
            row["key"] for row in await run("SELECT key FROM core_field_configs")
        ]
    finally:
        connection = await admin_connection()
        try:
            await connection.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        finally:
            await connection.close()


async def test_inferred_zeros_arrive_for_existing_releases_with_their_audit_entries():
    """0011 applies R8.1.3 to what is there: a missing day-0 Altmetric on a release whose paper
    came out that day or later becomes an inferred 0, with the note inferred_d0. Nothing else
    moves, and the downgrade takes the zeros back."""
    name = "release_radar_inferred_test"
    url = _PARSED_URL.set(database=name).render_as_string(hide_password=False)
    connection = await admin_connection()
    try:
        await connection.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        await connection.execute(f'CREATE DATABASE "{name}"')
    finally:
        await connection.close()

    import asyncpg

    async def run(statement: str, *arguments):
        database = await asyncpg.connect(
            host=_PARSED_URL.host,
            port=_PARSED_URL.port or 5432,
            user=_PARSED_URL.username,
            password=_PARSED_URL.password,
            database=name,
        )
        try:
            return await database.fetch(statement, *arguments)
        finally:
            await database.close()

    try:
        _migrate("upgrade", "0010", database_url=url)
        institution = (
            await run(
                "INSERT INTO institutions (id, name_en, timezone, ay_start_month, settings) "
                "VALUES (gen_random_uuid(), 'Existing', 'Asia/Tokyo', 4, '{}') RETURNING id"
            )
        )[0]["id"]
        checkpoint = (
            await run(
                "INSERT INTO checkpoints (id, institution_id, key, label_en, offset_days) "
                "VALUES (gen_random_uuid(), $1, 'd0', 'Release day', 0) RETURNING id",
                institution,
            )
        )[0]["id"]
        measures = {}
        for position, key in enumerate(("altmetric.d0", "ea_views.d28")):
            measures[key] = (
                await run(
                    "INSERT INTO measures (id, institution_id, key, metric, checkpoint_id, "
                    "source, applicability, unit, label_en, position, is_active) VALUES "
                    "(gen_random_uuid(), $1, $2, 'm', $3, 'manual', 'always', 'score', 'M', $4, "
                    "true) RETURNING id",
                    institution,
                    key,
                    checkpoint,
                    position,
                )
            )[0]["id"]
        cases = {
            # title: (publication date, reading state, value)
            "Same day": (date(2026, 4, 1), "missing", None),
            "Later": (date(2026, 4, 3), "missing", None),
            "Earlier": (date(2026, 3, 1), "missing", None),
            "No date": (None, "missing", None),
            "Typed": (date(2026, 4, 3), "value", 7),
            "Marked": (date(2026, 4, 3), "not_applicable", None),
        }
        readings = {}
        for title, (published, state, value) in cases.items():
            release = (
                await run(
                    "INSERT INTO releases (id, institution_id, title, authors, embargoed, "
                    "ea_top_page, custom_values, field_versions, release_date, "
                    "publication_date, doi) VALUES (gen_random_uuid(), $1, $2, '[]', false, "
                    "false, '{}', '{}', '2026-04-01', $3, '10.1234/x') RETURNING id",
                    institution,
                    title,
                    published,
                )
            )[0]["id"]
            for key, measure in measures.items():
                row = (
                    await run(
                        "INSERT INTO readings (id, institution_id, release_id, measure_id, "
                        "state, value, source, version) VALUES (gen_random_uuid(), $1, $2, $3, "
                        "$4, $5, $6, 3) RETURNING id",
                        institution,
                        release,
                        measure,
                        state if key == "altmetric.d0" else "missing",
                        value if key == "altmetric.d0" else None,
                        "manual" if state != "missing" and key == "altmetric.d0" else "auto",
                    )
                )[0]["id"]
                readings[(title, key)] = row

        upgraded = _alembic("upgrade", "0011", database_url=url)
        assert upgraded.returncode == 0, upgraded.stderr
        rows = {
            row["id"]: row
            for row in await run("SELECT id, state, value, source, inferred, version FROM readings")
        }

        def day0(title):
            return rows[readings[(title, "altmetric.d0")]]

        for title in ("Same day", "Later"):
            assert (day0(title)["state"], day0(title)["value"], day0(title)["inferred"]) == (
                "value",
                0,
                True,
            )
            assert day0(title)["version"] == 4
        for title in ("Earlier", "No date"):
            assert (day0(title)["state"], day0(title)["inferred"]) == ("missing", False)
        assert (day0("Typed")["value"], day0("Typed")["inferred"]) == (7, False)
        assert (day0("Marked")["state"], day0("Marked")["inferred"]) == ("not_applicable", False)
        assert not any(rows[readings[(title, "ea_views.d28")]]["inferred"] for title in cases)

        entries = await run(
            "SELECT entity_id, field, old_value::text AS old, new_value::text AS new, note "
            "FROM audit_log ORDER BY field"
        )
        assert {row["entity_id"] for row in entries} == {
            readings[("Same day", "altmetric.d0")],
            readings[("Later", "altmetric.d0")],
        }
        assert {row["note"] for row in entries} == {"inferred_d0"}
        later = [row for row in entries if row["entity_id"] == readings[("Later", "altmetric.d0")]]
        assert {(row["field"], row["old"], row["new"]) for row in later} == {
            ("inferred", "false", "true"),
            ("state", '"missing"', '"value"'),
            ("value", None, "0"),
            ("version", "3", "4"),
        }

        _migrate("downgrade", "0010", database_url=url)
        back = await run(
            "SELECT state, value FROM readings WHERE id = $1",
            readings[("Later", "altmetric.d0")],
        )
        assert (back[0]["state"], back[0]["value"]) == ("missing", None)
        assert (
            await run(
                "SELECT value FROM readings WHERE id = $1", readings[("Typed", "altmetric.d0")]
            )
        )[0]["value"] == 7
    finally:
        connection = await admin_connection()
        try:
            await connection.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        finally:
            await connection.close()
