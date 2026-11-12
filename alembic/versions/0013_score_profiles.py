"""score profiles (R8.2) and where the Analysis filters start (R6.4.2)

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-12 10:30:00.000000

Adds only. The default profile and the filters' starting types are seeded at start-up
(``app/seeds.py``), as every built-in is. The downgrade drops the profiles and their versions.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "score_profiles",
        sa.Column("key", sa.String(length=64), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("seeded", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_score_profiles_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_score_profiles_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
            name=op.f("fk_score_profiles_updated_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_score_profiles")),
        sa.UniqueConstraint("institution_id", "key", name="uq_score_profiles_key"),
    )
    op.create_index(
        op.f("ix_score_profiles_institution_id"), "score_profiles", ["institution_id"], unique=False
    )
    op.create_index(
        "uq_score_profiles_default",
        "score_profiles",
        ["institution_id"],
        unique=True,
        postgresql_where=sa.text("is_default"),
    )
    op.create_table(
        "score_profile_versions",
        sa.Column("profile_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name_en", sa.String(length=255), nullable=False),
        sa.Column("name_ja", sa.String(length=255), nullable=True),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.Column("weights", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("altmetric_basis", sa.String(length=16), nullable=False),
        sa.Column("coverage_min", sa.Integer(), nullable=False),
        sa.Column("comparison_years", sa.Integer(), nullable=False),
        sa.Column("min_values", sa.Integer(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.CheckConstraint(
            "altmetric_basis IN ('increase', 'd28')",
            name=op.f("ck_score_profile_versions_altmetric_basis_known"),
        ),
        sa.CheckConstraint(
            "comparison_years BETWEEN 1 AND 10",
            name=op.f("ck_score_profile_versions_comparison_years_range"),
        ),
        sa.CheckConstraint(
            "coverage_min BETWEEN 0 AND 100",
            name=op.f("ck_score_profile_versions_coverage_min_range"),
        ),
        sa.CheckConstraint(
            "min_values >= 1", name=op.f("ck_score_profile_versions_min_values_positive")
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_score_profile_versions_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_score_profile_versions_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["score_profiles.id"],
            name=op.f("fk_score_profile_versions_profile_id_score_profiles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
            name=op.f("fk_score_profile_versions_updated_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_score_profile_versions")),
        sa.UniqueConstraint("profile_id", "version", name="uq_score_profile_versions_version"),
    )
    op.create_index(
        op.f("ix_score_profile_versions_institution_id"),
        "score_profile_versions",
        ["institution_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_score_profile_versions_profile_id"),
        "score_profile_versions",
        ["profile_id"],
        unique=False,
    )
    op.add_column(
        "institutions",
        sa.Column(
            "analysed_release_type_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )
    op.add_column(
        "institutions",
        sa.Column("shown_release_type_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("institutions", "shown_release_type_ids")
    op.drop_column("institutions", "analysed_release_type_ids")
    op.drop_index(op.f("ix_score_profile_versions_profile_id"), table_name="score_profile_versions")
    op.drop_index(
        op.f("ix_score_profile_versions_institution_id"), table_name="score_profile_versions"
    )
    op.drop_table("score_profile_versions")
    op.drop_index(
        "uq_score_profiles_default",
        table_name="score_profiles",
        postgresql_where=sa.text("is_default"),
    )
    op.drop_index(op.f("ix_score_profiles_institution_id"), table_name="score_profiles")
    op.drop_table("score_profiles")
