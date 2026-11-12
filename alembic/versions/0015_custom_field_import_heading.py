"""the workbook column a custom field is filled from

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-12 21:00:00.000000

An import no longer knows any personal field by name (Daniel, 2026-11-12): a field remembers
the workbook column it is filled from, and a column nobody has a field for is offered to the
importing admin. The three fields the first import made remember their columns here: they
were made from exactly these headings (BRIEF step 1.8). Nothing else changes.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The label the first import gave each field, and the column it came from.
_MADE_BY_THE_FIRST_IMPORT = {
    "Bitly clicks, 28 days": "28 day engagements",
    "Pitches": "Pitches",
    "Request received": "Request received",
}


def upgrade() -> None:
    op.add_column("custom_fields", sa.Column("import_heading", sa.String(255), nullable=True))
    conn = op.get_bind()
    for label, heading in _MADE_BY_THE_FIRST_IMPORT.items():
        conn.execute(
            sa.text(
                "UPDATE custom_fields SET import_heading = CAST(:heading AS text)"
                " WHERE scope = 'personal' AND lower(label_en) = lower(CAST(:label AS text))"
            ),
            {"heading": heading, "label": label},
        )


def downgrade() -> None:
    op.drop_column("custom_fields", "import_heading")
