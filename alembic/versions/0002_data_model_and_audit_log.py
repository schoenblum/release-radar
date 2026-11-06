"""data model and audit log

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-06 17:05:54.619923
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("action", sa.String(length=8), nullable=False),
        sa.Column("field", sa.String(length=128), nullable=True),
        sa.Column(
            "old_value", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "new_value", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=True
        ),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.CheckConstraint(
            "action IN ('create', 'update', 'delete')", name=op.f("ck_audit_log_action_known")
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_audit_log_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_audit_log_user_id_users"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_log")),
    )
    op.create_index(
        "ix_audit_log_entity",
        "audit_log",
        ["institution_id", "entity_type", "entity_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_log_institution_id"), "audit_log", ["institution_id"], unique=False
    )
    op.create_index(op.f("ix_audit_log_user_id"), "audit_log", ["user_id"], unique=False)
    op.create_table(
        "checkpoints",
        sa.Column("key", sa.String(length=32), nullable=False),
        sa.Column("label_en", sa.String(length=255), nullable=False),
        sa.Column("label_ja", sa.String(length=255), nullable=True),
        sa.Column("offset_days", sa.Integer(), nullable=False),
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
        sa.CheckConstraint("offset_days >= 0", name=op.f("ck_checkpoints_offset_not_negative")),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_checkpoints_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_checkpoints_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
            name=op.f("fk_checkpoints_updated_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_checkpoints")),
        sa.UniqueConstraint("institution_id", "key", name="uq_checkpoints_key"),
    )
    op.create_index(
        op.f("ix_checkpoints_institution_id"), "checkpoints", ["institution_id"], unique=False
    )
    op.create_table(
        "core_field_configs",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("label_en", sa.String(length=255), nullable=True),
        sa.Column("label_ja", sa.String(length=255), nullable=True),
        sa.Column("hidden", sa.Boolean(), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_core_field_configs_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_core_field_configs_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
            name=op.f("fk_core_field_configs_updated_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_core_field_configs")),
        sa.UniqueConstraint("institution_id", "key", name="uq_core_field_configs_key"),
    )
    op.create_index(
        op.f("ix_core_field_configs_institution_id"),
        "core_field_configs",
        ["institution_id"],
        unique=False,
    )
    op.create_table(
        "research_fields",
        sa.Column("name_en", sa.String(length=255), nullable=False),
        sa.Column("name_ja", sa.String(length=255), nullable=True),
        sa.Column("scope_note", sa.Text(), nullable=True),
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
            name=op.f("fk_research_fields_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_research_fields_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
            name=op.f("fk_research_fields_updated_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_research_fields")),
        sa.UniqueConstraint("institution_id", "name_en", name="uq_research_fields_name"),
    )
    op.create_index(
        op.f("ix_research_fields_institution_id"),
        "research_fields",
        ["institution_id"],
        unique=False,
    )
    op.create_table(
        "vocabularies",
        sa.Column("key", sa.String(length=64), nullable=False),
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
            name=op.f("fk_vocabularies_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_vocabularies_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
            name=op.f("fk_vocabularies_updated_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_vocabularies")),
        sa.UniqueConstraint("institution_id", "key", name="uq_vocabularies_key"),
    )
    op.create_index(
        op.f("ix_vocabularies_institution_id"), "vocabularies", ["institution_id"], unique=False
    )
    op.create_table(
        "writers",
        sa.Column("display_name_en", sa.String(length=255), nullable=False),
        sa.Column("display_name_ja", sa.String(length=255), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
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
            name=op.f("fk_writers_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_writers_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
            name=op.f("fk_writers_updated_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_writers_user_id_users"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_writers")),
        sa.UniqueConstraint("institution_id", "user_id", name="uq_writers_user"),
    )
    op.create_index(op.f("ix_writers_institution_id"), "writers", ["institution_id"], unique=False)
    op.create_table(
        "custom_fields",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("label_en", sa.String(length=255), nullable=False),
        sa.Column("label_ja", sa.String(length=255), nullable=True),
        sa.Column("help_en", sa.Text(), nullable=True),
        sa.Column("help_ja", sa.Text(), nullable=True),
        sa.Column("field_type", sa.String(length=16), nullable=False),
        sa.Column("options", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("vocabulary_id", sa.UUID(), nullable=True),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("due_checkpoint_id", sa.UUID(), nullable=True),
        sa.Column("score_eligible", sa.Boolean(), nullable=False),
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
            "(scope = 'personal') = (owner_id IS NOT NULL)",
            name=op.f("ck_custom_fields_owner_matches_scope"),
        ),
        sa.CheckConstraint(
            "NOT required OR scope = 'institution'",
            name=op.f("ck_custom_fields_required_institution_only"),
        ),
        sa.CheckConstraint(
            "NOT score_eligible OR (scope = 'institution' AND field_type IN ('integer', 'number'))",
            name=op.f("ck_custom_fields_score_eligible_numeric_institution"),
        ),
        sa.CheckConstraint(
            "field_type IN ('integer', 'number', 'text', 'long_text', 'date', 'boolean', 'single_select', 'multi_select', 'url')",
            name=op.f("ck_custom_fields_field_type_known"),
        ),
        sa.CheckConstraint(
            "scope IN ('institution', 'personal')", name=op.f("ck_custom_fields_scope_known")
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_custom_fields_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["due_checkpoint_id"],
            ["checkpoints.id"],
            name=op.f("fk_custom_fields_due_checkpoint_id_checkpoints"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_custom_fields_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name=op.f("fk_custom_fields_owner_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
            name=op.f("fk_custom_fields_updated_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["vocabulary_id"],
            ["vocabularies.id"],
            name=op.f("fk_custom_fields_vocabulary_id_vocabularies"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_custom_fields")),
        sa.UniqueConstraint("institution_id", "key", name="uq_custom_fields_key"),
    )
    op.create_index(
        op.f("ix_custom_fields_institution_id"), "custom_fields", ["institution_id"], unique=False
    )
    op.create_index(op.f("ix_custom_fields_owner_id"), "custom_fields", ["owner_id"], unique=False)
    op.create_table(
        "measures",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("metric", sa.String(length=64), nullable=False),
        sa.Column("checkpoint_id", sa.UUID(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("applicability", sa.String(length=32), nullable=False),
        sa.Column("unit", sa.String(length=16), nullable=False),
        sa.Column("label_en", sa.String(length=255), nullable=False),
        sa.Column("label_ja", sa.String(length=255), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("collected_from", sa.Date(), nullable=True),
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
            "applicability IN ('always', 'embargoed', 'has_doi', 'has_ea_url', 'website_on_domain')",
            name=op.f("ck_measures_applicability_known"),
        ),
        sa.ForeignKeyConstraint(
            ["checkpoint_id"],
            ["checkpoints.id"],
            name=op.f("fk_measures_checkpoint_id_checkpoints"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_measures_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_measures_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
            name=op.f("fk_measures_updated_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_measures")),
        sa.UniqueConstraint("institution_id", "key", name="uq_measures_key"),
    )
    op.create_index(
        op.f("ix_measures_institution_id"), "measures", ["institution_id"], unique=False
    )
    op.create_table(
        "units",
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("name_en", sa.String(length=255), nullable=False),
        sa.Column("name_ja", sa.String(length=255), nullable=True),
        sa.Column("short_label", sa.String(length=64), nullable=True),
        sa.Column("unit_type", sa.String(length=16), nullable=True),
        sa.Column("aliases", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("default_field_id", sa.UUID(), nullable=True),
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
        sa.CheckConstraint(
            "unit_type IN ('school', 'institute', 'center', 'other')",
            name=op.f("ck_units_unit_type_known"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_units_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["default_field_id"],
            ["research_fields.id"],
            name=op.f("fk_units_default_field_id_research_fields"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_units_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
            name=op.f("fk_units_updated_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_units")),
        sa.UniqueConstraint("institution_id", "key", name="uq_units_key"),
    )
    op.create_index(op.f("ix_units_institution_id"), "units", ["institution_id"], unique=False)
    op.create_table(
        "vocabulary_items",
        sa.Column("vocabulary_id", sa.UUID(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("label_en", sa.String(length=255), nullable=False),
        sa.Column("label_ja", sa.String(length=255), nullable=True),
        sa.Column("aliases", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
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
            name=op.f("fk_vocabulary_items_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_vocabulary_items_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
            name=op.f("fk_vocabulary_items_updated_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["vocabulary_id"],
            ["vocabularies.id"],
            name=op.f("fk_vocabulary_items_vocabulary_id_vocabularies"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_vocabulary_items")),
        sa.UniqueConstraint("vocabulary_id", "key", name="uq_vocabulary_items_key"),
    )
    op.create_index(
        op.f("ix_vocabulary_items_institution_id"),
        "vocabulary_items",
        ["institution_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_vocabulary_items_vocabulary_id"),
        "vocabulary_items",
        ["vocabulary_id"],
        unique=False,
    )
    op.create_table(
        "researchers",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("given_name", sa.String(length=255), nullable=True),
        sa.Column("family_name", sa.String(length=255), nullable=True),
        sa.Column("name_ja", sa.String(length=255), nullable=True),
        sa.Column("current_unit_id", sa.UUID(), nullable=True),
        sa.Column("gender", sa.String(length=16), nullable=False),
        sa.Column("researchmap_id", sa.String(length=255), nullable=True),
        sa.Column("orcid", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("merged_into_id", sa.UUID(), nullable=True),
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
        sa.Column(
            "field_versions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "gender IN ('M', 'F', 'other', 'not_recorded')",
            name=op.f("ck_researchers_gender_known"),
        ),
        sa.CheckConstraint(
            "status IN ('incomplete', 'unverified', 'verified')",
            name=op.f("ck_researchers_status_known"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_researchers_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["current_unit_id"],
            ["units.id"],
            name=op.f("fk_researchers_current_unit_id_units"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_researchers_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["merged_into_id"],
            ["researchers.id"],
            name=op.f("fk_researchers_merged_into_id_researchers"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
            name=op.f("fk_researchers_updated_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_researchers")),
    )
    op.create_index(
        op.f("ix_researchers_institution_id"), "researchers", ["institution_id"], unique=False
    )
    op.create_table(
        "releases",
        sa.Column("code", sa.String(length=32), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("title_ja", sa.Text(), nullable=True),
        sa.Column("writer_id", sa.UUID(), nullable=True),
        sa.Column("researcher_id", sa.UUID(), nullable=True),
        sa.Column("also_featured", sa.Text(), nullable=True),
        sa.Column("unit_id", sa.UUID(), nullable=True),
        sa.Column("field_id", sa.UUID(), nullable=True),
        sa.Column("doi", sa.String(length=255), nullable=True),
        sa.Column("journal", sa.Text(), nullable=True),
        sa.Column("paper_title", sa.Text(), nullable=True),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("authors", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("embargoed", sa.Boolean(), nullable=False),
        sa.Column("release_date", sa.Date(), nullable=True),
        sa.Column("release_time_et", sa.Time(), nullable=True),
        sa.Column("ea_url", sa.Text(), nullable=True),
        sa.Column("website_url", sa.Text(), nullable=True),
        sa.Column("ea_top_page", sa.Boolean(), nullable=False),
        sa.Column("ea_top_position", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("custom_values", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
        sa.Column(
            "field_versions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "ea_top_position IS NULL OR (ea_top_page AND ea_top_position >= 1)",
            name=op.f("ck_releases_ea_top_position_valid"),
        ),
        sa.CheckConstraint(
            "title IS NOT NULL OR doi IS NOT NULL", name=op.f("ck_releases_title_or_doi")
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_releases_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["field_id"],
            ["research_fields.id"],
            name=op.f("fk_releases_field_id_research_fields"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_releases_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["researcher_id"],
            ["researchers.id"],
            name=op.f("fk_releases_researcher_id_researchers"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["unit_id"], ["units.id"], name=op.f("fk_releases_unit_id_units"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
            name=op.f("fk_releases_updated_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["writer_id"],
            ["writers.id"],
            name=op.f("fk_releases_writer_id_writers"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_releases")),
        sa.UniqueConstraint("institution_id", "code", name="uq_releases_code"),
    )
    op.create_index(op.f("ix_releases_doi"), "releases", ["doi"], unique=False)
    op.create_index(op.f("ix_releases_field_id"), "releases", ["field_id"], unique=False)
    op.create_index(
        op.f("ix_releases_institution_id"), "releases", ["institution_id"], unique=False
    )
    op.create_index(
        "ix_releases_institution_release_date",
        "releases",
        ["institution_id", "release_date"],
        unique=False,
    )
    op.create_index(op.f("ix_releases_researcher_id"), "releases", ["researcher_id"], unique=False)
    op.create_index(op.f("ix_releases_unit_id"), "releases", ["unit_id"], unique=False)
    op.create_index(op.f("ix_releases_writer_id"), "releases", ["writer_id"], unique=False)
    op.create_table(
        "readings",
        sa.Column("release_id", sa.UUID(), nullable=False),
        sa.Column("measure_id", sa.UUID(), nullable=False),
        sa.Column("value", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("source", sa.String(length=8), nullable=False),
        sa.Column("entered_by_id", sa.UUID(), nullable=True),
        sa.Column("entered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
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
            "(state = 'value') = (value IS NOT NULL)", name=op.f("ck_readings_value_matches_state")
        ),
        sa.CheckConstraint("source IN ('manual', 'auto')", name=op.f("ck_readings_source_known")),
        sa.CheckConstraint(
            "state IN ('value', 'not_applicable', 'missing')", name=op.f("ck_readings_state_known")
        ),
        sa.CheckConstraint("value >= 0", name=op.f("ck_readings_value_not_negative")),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_readings_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["entered_by_id"],
            ["users.id"],
            name=op.f("fk_readings_entered_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_readings_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["measure_id"],
            ["measures.id"],
            name=op.f("fk_readings_measure_id_measures"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["release_id"],
            ["releases.id"],
            name=op.f("fk_readings_release_id_releases"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
            name=op.f("fk_readings_updated_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_readings")),
        sa.UniqueConstraint("release_id", "measure_id", name="uq_readings_release_measure"),
    )
    op.create_index(
        op.f("ix_readings_institution_id"), "readings", ["institution_id"], unique=False
    )
    op.create_index(op.f("ix_readings_measure_id"), "readings", ["measure_id"], unique=False)
    op.add_column("institutions", sa.Column("website_domain", sa.String(length=255), nullable=True))
    op.add_column(
        "institutions",
        sa.Column(
            "ea_url_pattern",
            sa.Text(),
            server_default="^https://www\\.eurekalert\\.org/news-releases/\\d+$",
            nullable=False,
        ),
    )
    op.add_column(
        "institutions",
        sa.Column(
            "release_code_pattern",
            sa.String(length=64),
            server_default="AY{yyyy}-{nn}",
            nullable=False,
        ),
    )
    op.add_column(
        "institutions",
        sa.Column(
            "landing_pages",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text(
                '\'{"admin": "mine", "editor": "mine", "viewer": "all"}\'::jsonb'
            ),
            nullable=False,
        ),
    )
    op.add_column(
        "institutions",
        sa.Column(
            "major_outlet_threshold", sa.BigInteger(), server_default="1000000", nullable=False
        ),
    )
    op.add_column("institutions", sa.Column("contact_email", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("institutions", "contact_email")
    op.drop_column("institutions", "major_outlet_threshold")
    op.drop_column("institutions", "landing_pages")
    op.drop_column("institutions", "release_code_pattern")
    op.drop_column("institutions", "ea_url_pattern")
    op.drop_column("institutions", "website_domain")
    op.drop_index(op.f("ix_readings_measure_id"), table_name="readings")
    op.drop_index(op.f("ix_readings_institution_id"), table_name="readings")
    op.drop_table("readings")
    op.drop_index(op.f("ix_releases_writer_id"), table_name="releases")
    op.drop_index(op.f("ix_releases_unit_id"), table_name="releases")
    op.drop_index(op.f("ix_releases_researcher_id"), table_name="releases")
    op.drop_index("ix_releases_institution_release_date", table_name="releases")
    op.drop_index(op.f("ix_releases_institution_id"), table_name="releases")
    op.drop_index(op.f("ix_releases_field_id"), table_name="releases")
    op.drop_index(op.f("ix_releases_doi"), table_name="releases")
    op.drop_table("releases")
    op.drop_index(op.f("ix_researchers_institution_id"), table_name="researchers")
    op.drop_table("researchers")
    op.drop_index(op.f("ix_vocabulary_items_vocabulary_id"), table_name="vocabulary_items")
    op.drop_index(op.f("ix_vocabulary_items_institution_id"), table_name="vocabulary_items")
    op.drop_table("vocabulary_items")
    op.drop_index(op.f("ix_units_institution_id"), table_name="units")
    op.drop_table("units")
    op.drop_index(op.f("ix_measures_institution_id"), table_name="measures")
    op.drop_table("measures")
    op.drop_index(op.f("ix_custom_fields_owner_id"), table_name="custom_fields")
    op.drop_index(op.f("ix_custom_fields_institution_id"), table_name="custom_fields")
    op.drop_table("custom_fields")
    op.drop_index(op.f("ix_writers_institution_id"), table_name="writers")
    op.drop_table("writers")
    op.drop_index(op.f("ix_vocabularies_institution_id"), table_name="vocabularies")
    op.drop_table("vocabularies")
    op.drop_index(op.f("ix_research_fields_institution_id"), table_name="research_fields")
    op.drop_table("research_fields")
    op.drop_index(op.f("ix_core_field_configs_institution_id"), table_name="core_field_configs")
    op.drop_table("core_field_configs")
    op.drop_index(op.f("ix_checkpoints_institution_id"), table_name="checkpoints")
    op.drop_table("checkpoints")
    op.drop_index(op.f("ix_audit_log_user_id"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_institution_id"), table_name="audit_log")
    op.drop_index("ix_audit_log_entity", table_name="audit_log")
    op.drop_table("audit_log")
