"""built-in fields: shown in the grid, shown in the record

Revision ID: 0016
Revises: 0015
Create Date: 2026-11-12 23:10:00.000000

Settings → Form had one "Hidden" box per built-in field, which hid it everywhere. Daniel
(2026-11-12) asked for two: whether the grid shows the field (for everyone who has not chosen
their own columns) and whether the record does. ``hidden`` becomes ``in_record`` with the
opposite value, so nothing is lost; ``in_grid`` starts with the columns the grid has shown by
default so far, among the fields not hidden. The field versions follow the rename.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The grid's default columns until now (frontend `columns.ts`, DEFAULT_CORE, at 0.14.0).
_GRID_BEFORE = (
    "code",
    "title",
    "release_date",
    "researcher",
    "researcher_gender",
    "unit",
    "field",
    "release_type",
    "doi",
    "publication_date",
    "embargoed",
    "ea_url",
    "website_url",
    "ea_top_page",
)


def _rename_version(old: str, new: str) -> None:
    op.execute(
        sa.text(
            "UPDATE core_field_configs SET field_versions = (field_versions - CAST(:old AS text))"
            " || jsonb_build_object(CAST(:new AS text), field_versions -> CAST(:old AS text))"
            " WHERE field_versions ? CAST(:old AS text)"
        ).bindparams(old=old, new=new)
    )


def upgrade() -> None:
    op.alter_column("core_field_configs", "hidden", new_column_name="in_record")
    op.execute("UPDATE core_field_configs SET in_record = NOT in_record")
    _rename_version("hidden", "in_record")
    op.add_column(
        "core_field_configs",
        sa.Column("in_grid", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute(
        sa.text(
            "UPDATE core_field_configs SET in_grid = in_record AND key = ANY(CAST(:keys AS text[]))"
        ).bindparams(keys=list(_GRID_BEFORE))
    )
    op.alter_column("core_field_configs", "in_grid", server_default=None)


def downgrade() -> None:
    op.drop_column("core_field_configs", "in_grid")
    _rename_version("in_record", "hidden")
    op.execute("UPDATE core_field_configs SET in_record = NOT in_record")
    op.alter_column("core_field_configs", "in_record", new_column_name="hidden")
