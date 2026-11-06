"""field versions on settings records

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-06 17:37:36.069381
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "checkpoints",
        sa.Column(
            "field_versions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "core_field_configs",
        sa.Column(
            "field_versions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "custom_fields",
        sa.Column(
            "field_versions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "institutions",
        sa.Column(
            "field_versions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "measures",
        sa.Column(
            "field_versions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "research_fields",
        sa.Column(
            "field_versions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "units",
        sa.Column(
            "field_versions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "vocabularies",
        sa.Column(
            "field_versions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "vocabulary_items",
        sa.Column(
            "field_versions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "writers",
        sa.Column(
            "field_versions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("writers", "field_versions")
    op.drop_column("vocabulary_items", "field_versions")
    op.drop_column("vocabularies", "field_versions")
    op.drop_column("units", "field_versions")
    op.drop_column("research_fields", "field_versions")
    op.drop_column("measures", "field_versions")
    op.drop_column("institutions", "field_versions")
    op.drop_column("custom_fields", "field_versions")
    op.drop_column("core_field_configs", "field_versions")
    op.drop_column("checkpoints", "field_versions")
