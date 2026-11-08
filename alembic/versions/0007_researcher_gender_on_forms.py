"""the researcher's gender becomes a built-in field on forms, right after the researcher

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-08 15:00:00.000000

Adds one settings row per institution (shown, not required) and renumbers the order around
it. The gender itself stays on the researcher's record; nothing moves.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

KEY = "researcher_gender"


def upgrade() -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT id, institution_id, key FROM core_field_configs "
            "ORDER BY institution_id, position, key"
        )
    ).all()
    by_institution: dict[object, list[tuple[object, str]]] = {}
    for row_id, institution_id, key in rows:
        by_institution.setdefault(institution_id, []).append((row_id, key))
    for institution_id, fields in by_institution.items():
        keys = [key for _, key in fields]
        if KEY in keys:
            continue
        new_id = connection.execute(
            sa.text(
                "INSERT INTO core_field_configs (id, institution_id, key, hidden, required, "
                "position) VALUES (gen_random_uuid(), :institution, :key, false, false, 0) "
                "RETURNING id"
            ),
            {"institution": institution_id, "key": KEY},
        ).scalar_one()
        place = keys.index("researcher") + 1 if "researcher" in keys else len(fields)
        fields.insert(place, (new_id, KEY))
        for position, (row_id, _) in enumerate(fields):
            connection.execute(
                sa.text("UPDATE core_field_configs SET position = :position WHERE id = :id"),
                {"position": position, "id": row_id},
            )


def downgrade() -> None:
    op.get_bind().execute(sa.text("DELETE FROM core_field_configs WHERE key = :key"), {"key": KEY})
