"""release time in the institution's time zone, and further zones to show it in

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-12 18:00:00.000000

The release time was US Eastern, and the release date with it (they came from EurekAlert).
Both now mean the institution's time zone (Daniel, 2026-11-12): every release with a date and
a time is converted, and its date can move by a day. Each change goes to the audit log, as an
edit in the app would. A moved date moves a fetched number's 28 days, so such a number is
cleared to be fetched again, as the app does when a date changes (``app.services.readings``).

Plain SQL rather than the app's models, which may differ from this revision's schema later.
The downgrade converts back.
"""

import json
import uuid
from collections.abc import Sequence
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EASTERN = "America/New_York"
NOTE_UP = "Converted from US Eastern time to the institution's time zone (migration 0014)"
NOTE_DOWN = "Converted back to US Eastern time (migration 0014, downgrade)"


def _convert(day: date, clock: time, source: str, target: str) -> tuple[date, time]:
    moment = datetime.combine(day, clock, tzinfo=ZoneInfo(source))
    moved = moment.astimezone(ZoneInfo(target))
    return moved.date(), moved.time().replace(tzinfo=None)


def _audit(conn: sa.Connection, institution_id, entity: str, entity_id, field, old, new, note):
    conn.execute(
        sa.text(
            "INSERT INTO audit_log (id, institution_id, entity_type, entity_id, action, field,"
            " old_value, new_value, user_id, note)"
            " VALUES (:id, :institution, :entity, :entity_id, 'update', :field,"
            " CAST(:old AS jsonb), CAST(:new AS jsonb), NULL, :note)"
        ),
        {
            "id": uuid.uuid4(),
            "institution": institution_id,
            "entity": entity,
            "entity_id": entity_id,
            "field": field,
            "old": json.dumps(old),
            "new": json.dumps(new),
            "note": note,
        },
    )


def _move_times(conn: sa.Connection, source_of, target_of, note: str) -> None:
    """Convert every release's date and time from one zone to another, with audit entries."""
    column = "release_time"
    rows = conn.execute(
        sa.text(
            "SELECT r.id, r.institution_id, r.release_date, r.release_time, r.field_versions,"
            " i.timezone FROM releases r JOIN institutions i ON i.id = r.institution_id"
            " WHERE r.release_date IS NOT NULL AND r.release_time IS NOT NULL"
        )
    ).all()
    for release_id, institution_id, day, clock, versions, zone in rows:
        new_day, new_clock = _convert(day, clock, source_of(zone), target_of(zone))
        versions = dict(versions or {})
        if new_clock != clock:
            versions[column] = versions.get(column, 0) + 1
            _audit(
                conn,
                institution_id,
                "releases",
                release_id,
                column,
                clock.isoformat(),
                new_clock.isoformat(),
                note,
            )
        if new_day != day:
            versions["release_date"] = versions.get("release_date", 0) + 1
            _audit(
                conn,
                institution_id,
                "releases",
                release_id,
                "release_date",
                day.isoformat(),
                new_day.isoformat(),
                note,
            )
            _refetch(conn, institution_id, release_id, note)
        conn.execute(
            sa.text(
                "UPDATE releases SET release_date = :day, release_time = :clock,"
                " field_versions = CAST(:versions AS jsonb) WHERE id = :id"
            ),
            {
                "day": new_day,
                "clock": new_clock,
                "versions": json.dumps(versions),
                "id": release_id,
            },
        )


def _refetch(conn: sa.Connection, institution_id, release_id, note: str) -> None:
    """A fetched number was for the old 28 days: clear it, so the next run fetches it again."""
    readings = conn.execute(
        sa.text(
            "SELECT rd.id, rd.value FROM readings rd JOIN measures m ON m.id = rd.measure_id"
            " WHERE rd.release_id = :release AND m.source = 'ga4' AND rd.state = 'value'"
            " AND rd.source = 'auto' AND NOT rd.inferred"
        ),
        {"release": release_id},
    ).all()
    for reading_id, value in readings:
        conn.execute(
            sa.text(
                "UPDATE readings SET value = NULL, state = 'missing', version = version + 1"
                " WHERE id = :id"
            ),
            {"id": reading_id},
        )
        _audit(conn, institution_id, "readings", reading_id, "value", float(value), None, note)
        _audit(conn, institution_id, "readings", reading_id, "state", "value", "missing", note)


def _rename_key(conn: sa.Connection, old: str, new: str) -> None:
    """The field's name where settings and versions keep it."""
    conn.execute(
        sa.text(
            "UPDATE core_field_configs SET key = CAST(:new AS text) WHERE key = CAST(:old AS text)"
        ),
        {"old": old, "new": new},
    )
    conn.execute(
        sa.text(
            "UPDATE releases SET field_versions = (field_versions - CAST(:old AS text))"
            " || jsonb_build_object(CAST(:new AS text), field_versions -> CAST(:old AS text))"
            " WHERE field_versions ? CAST(:old AS text)"
        ),
        {"old": old, "new": new},
    )
    # A person's saved columns name it too.
    conn.execute(
        sa.text(
            "UPDATE users SET preferences ="
            " CAST(replace(preferences::text, CAST(:old AS text), CAST(:new AS text)) AS jsonb)"
            " WHERE preferences::text LIKE CAST(:like AS text)"
        ),
        {"old": f'"{old}"', "new": f'"{new}"', "like": f'%"{old}"%'},
    )


def upgrade() -> None:
    op.add_column(
        "institutions",
        sa.Column(
            "display_time_zones",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text(f"""'["{EASTERN}"]'::jsonb"""),
        ),
    )
    op.alter_column("releases", "release_time_et", new_column_name="release_time")
    conn = op.get_bind()
    _rename_key(conn, "release_time_et", "release_time")
    _move_times(conn, lambda _zone: EASTERN, lambda zone: zone, NOTE_UP)


def downgrade() -> None:
    conn = op.get_bind()
    _move_times(conn, lambda zone: zone, lambda _zone: EASTERN, NOTE_DOWN)
    _rename_key(conn, "release_time", "release_time_et")
    op.alter_column("releases", "release_time", new_column_name="release_time_et")
    op.drop_column("institutions", "display_time_zones")
