"""the paper's publication date moves next to the DOI on forms

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-08 12:00:00.000000

Changes only the order of built-in fields, which admins can change back on Settings → Form.
Nothing is added or removed.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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
    for fields in by_institution.values():
        keys = [key for _, key in fields]
        if "doi" not in keys or "publication_date" not in keys:
            continue
        moved = fields.pop(keys.index("publication_date"))
        fields.insert([key for _, key in fields].index("doi") + 1, moved)
        for position, (row_id, _) in enumerate(fields):
            connection.execute(
                sa.text("UPDATE core_field_configs SET position = :position WHERE id = :id"),
                {"position": position, "id": row_id},
            )


def downgrade() -> None:
    # Only an order changed, and an admin may have reordered since: leave it as it is.
    pass
