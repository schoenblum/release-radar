"""inferred day-0 Altmetric (R8.1.3, D27): a reading can be a rule's 0, marked as such

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-09 16:00:00.000000

Adds ``readings.inferred``, then applies the rule to every release there is: a day-0 Altmetric
reading that is missing (not N/A, not entered by hand) on a release whose paper was published
on or after its release date becomes 0, inferred. Bulk SQL, so the audit entries are written
here, with the note ``inferred_d0``, as the save hooks would have written them. The downgrade
turns those zeros back into missing and drops the column.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# A copy of app.services.readings.INFERRED_ZERO as it is today.
MEASURE = "altmetric.d0"
NOTE = "inferred_d0"


def upgrade() -> None:
    op.add_column(
        "readings",
        sa.Column("inferred", sa.Boolean(), server_default="false", nullable=False),
    )
    op.create_check_constraint(
        op.f("ck_readings_inferred_is_a_rules_zero"),
        "readings",
        "NOT inferred OR (state = 'value' AND value = 0 AND source = 'auto')",
    )
    op.execute(
        sa.text(
            """
            WITH target AS (
                SELECT reading.id, reading.version
                FROM readings AS reading
                JOIN measures AS measure ON measure.id = reading.measure_id
                JOIN releases AS release ON release.id = reading.release_id
                WHERE measure.key = :measure
                  AND reading.state = 'missing'
                  AND release.release_date IS NOT NULL
                  AND release.publication_date IS NOT NULL
                  AND release.publication_date >= release.release_date
            ),
            changed AS (
                UPDATE readings AS reading
                SET value = 0, state = 'value', source = 'auto', inferred = true,
                    version = reading.version + 1, updated_at = now()
                FROM target
                WHERE reading.id = target.id
                RETURNING reading.id, reading.institution_id, target.version AS old_version
            )
            INSERT INTO audit_log
                (id, institution_id, entity_type, entity_id, action, field, old_value,
                 new_value, user_id, note, created_at)
            SELECT gen_random_uuid(), changed.institution_id, 'readings', changed.id, 'update',
                   entry.field, entry.old_value, entry.new_value, NULL, :note, now()
            FROM changed
            CROSS JOIN LATERAL (
                VALUES
                    ('value', NULL::jsonb, '0'::jsonb),
                    ('state', '"missing"'::jsonb, '"value"'::jsonb),
                    ('version', to_jsonb(changed.old_version), to_jsonb(changed.old_version + 1)),
                    ('inferred', 'false'::jsonb, 'true'::jsonb)
            ) AS entry (field, old_value, new_value)
            """
        ).bindparams(measure=MEASURE, note=NOTE)
    )


def downgrade() -> None:
    # The check first: it holds that an inferred reading is a 0.
    op.drop_constraint(op.f("ck_readings_inferred_is_a_rules_zero"), "readings", type_="check")
    op.execute(
        "UPDATE readings SET value = NULL, state = 'missing', version = version + 1 WHERE inferred"
    )
    op.drop_column("readings", "inferred")
