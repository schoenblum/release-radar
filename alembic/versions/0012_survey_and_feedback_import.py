"""researcher feedback (R8.1.2, R11.1): survey templates, items and responses; the import kind

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-09 16:45:00.000000

Adds only. Every existing import run is a workbook run. The downgrade drops the survey tables,
imported responses included, so take a dump first.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "survey_templates",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name_en", sa.String(length=255), nullable=False),
        sa.Column("name_ja", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
            name=op.f("fk_survey_templates_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_survey_templates_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
            name=op.f("fk_survey_templates_updated_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_survey_templates")),
        sa.UniqueConstraint("institution_id", "key", "version", name="uq_survey_templates_version"),
    )
    op.create_index(
        op.f("ix_survey_templates_institution_id"),
        "survey_templates",
        ["institution_id"],
        unique=False,
    )
    op.create_table(
        "survey_items",
        sa.Column("template_id", sa.UUID(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("question", sa.String(length=32), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("exclusive", sa.Boolean(), nullable=False),
        sa.Column("external", sa.Boolean(), nullable=False),
        sa.Column("label_en", sa.Text(), nullable=False),
        sa.Column("label_ja", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
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
            "kind IN ('flag', 'scale', 'text')", name=op.f("ck_survey_items_kind_known")
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_survey_items_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_survey_items_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["survey_templates.id"],
            name=op.f("fk_survey_items_template_id_survey_templates"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
            name=op.f("fk_survey_items_updated_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_survey_items")),
        sa.UniqueConstraint("template_id", "key", name="uq_survey_items_key"),
    )
    op.create_index(
        op.f("ix_survey_items_institution_id"), "survey_items", ["institution_id"], unique=False
    )
    op.create_index(
        op.f("ix_survey_items_template_id"), "survey_items", ["template_id"], unique=False
    )
    op.create_table(
        "survey_responses",
        sa.Column("template_id", sa.UUID(), nullable=False),
        sa.Column("release_id", sa.UUID(), nullable=True),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("external_id", sa.String(length=64), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("language", sa.String(length=8), nullable=True),
        sa.Column("respondent_name", sa.Text(), nullable=True),
        sa.Column("answers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("other_texts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
            "source IN ('legacy_import', 'survey')", name=op.f("ck_survey_responses_source_known")
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_survey_responses_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_survey_responses_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["release_id"],
            ["releases.id"],
            name=op.f("fk_survey_responses_release_id_releases"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["survey_templates.id"],
            name=op.f("fk_survey_responses_template_id_survey_templates"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
            name=op.f("fk_survey_responses_updated_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_survey_responses")),
        sa.UniqueConstraint(
            "institution_id", "source", "external_id", name="uq_survey_responses_external"
        ),
    )
    op.create_index(
        op.f("ix_survey_responses_institution_id"),
        "survey_responses",
        ["institution_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_survey_responses_release_id"), "survey_responses", ["release_id"], unique=False
    )
    op.create_index(
        op.f("ix_survey_responses_template_id"), "survey_responses", ["template_id"], unique=False
    )
    op.add_column(
        "import_runs",
        sa.Column("kind", sa.String(length=16), server_default="workbook", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("import_runs", "kind")
    op.drop_index(op.f("ix_survey_responses_template_id"), table_name="survey_responses")
    op.drop_index(op.f("ix_survey_responses_release_id"), table_name="survey_responses")
    op.drop_index(op.f("ix_survey_responses_institution_id"), table_name="survey_responses")
    op.drop_table("survey_responses")
    op.drop_index(op.f("ix_survey_items_template_id"), table_name="survey_items")
    op.drop_index(op.f("ix_survey_items_institution_id"), table_name="survey_items")
    op.drop_table("survey_items")
    op.drop_index(op.f("ix_survey_templates_institution_id"), table_name="survey_templates")
    op.drop_table("survey_templates")
