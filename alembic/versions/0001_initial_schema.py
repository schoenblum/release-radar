"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-11-06 16:06:44.710546
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "institutions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name_en", sa.String(length=255), nullable=False),
        sa.Column("name_ja", sa.String(length=255), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("ay_start_month", sa.Integer(), nullable=False),
        sa.Column("settings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
        sa.CheckConstraint(
            "ay_start_month BETWEEN 1 AND 12", name=op.f("ck_institutions_ay_start_month_range")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_institutions")),
    )
    op.create_table(
        "job_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("job_key", sa.String(length=64), nullable=False),
        sa.Column("slot", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("worker", sa.String(length=128), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'skipped', 'failed')",
            name=op.f("ck_job_runs_status_known"),
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_job_runs_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_runs")),
        sa.UniqueConstraint("institution_id", "job_key", "slot", name="uq_job_runs_slot"),
    )
    op.create_index(
        op.f("ix_job_runs_institution_id"), "job_runs", ["institution_id"], unique=False
    )
    op.create_index(op.f("ix_job_runs_job_key"), "job_runs", ["job_key"], unique=False)
    op.create_table(
        "rate_limit_hits",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("bucket", sa.String(length=64), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_rate_limit_hits_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rate_limit_hits")),
        sa.UniqueConstraint(
            "institution_id", "bucket", "window_start", name="uq_rate_limit_window"
        ),
    )
    op.create_index(
        op.f("ix_rate_limit_hits_institution_id"),
        "rate_limit_hits",
        ["institution_id"],
        unique=False,
    )
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "admin",
                "editor",
                "viewer",
                name="user_role",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("language", sa.String(length=2), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("force_password_change", sa.Boolean(), nullable=False),
        sa.Column("token_version", sa.Integer(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint("language IN ('en', 'ja')", name=op.f("ck_users_language_supported")),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_users_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_users_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
            name=op.f("fk_users_updated_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("institution_id", "email", name="uq_users_institution_email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)
    op.create_index(op.f("ix_users_institution_id"), "users", ["institution_id"], unique=False)
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_password_reset_tokens_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_password_reset_tokens_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_password_reset_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_password_reset_tokens_token_hash")),
    )
    op.create_index(
        op.f("ix_password_reset_tokens_institution_id"),
        "password_reset_tokens",
        ["institution_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_password_reset_tokens_user_id"), "password_reset_tokens", ["user_id"], unique=False
    )
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_used_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_refresh_tokens_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_refresh_tokens_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_refresh_tokens_token_hash")),
    )
    op.create_index(
        op.f("ix_refresh_tokens_institution_id"), "refresh_tokens", ["institution_id"], unique=False
    )
    op.create_index(op.f("ix_refresh_tokens_user_id"), "refresh_tokens", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_refresh_tokens_user_id"), table_name="refresh_tokens")
    op.drop_index(op.f("ix_refresh_tokens_institution_id"), table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_index(op.f("ix_password_reset_tokens_user_id"), table_name="password_reset_tokens")
    op.drop_index(
        op.f("ix_password_reset_tokens_institution_id"), table_name="password_reset_tokens"
    )
    op.drop_table("password_reset_tokens")
    op.drop_index(op.f("ix_users_institution_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_rate_limit_hits_institution_id"), table_name="rate_limit_hits")
    op.drop_table("rate_limit_hits")
    op.drop_index(op.f("ix_job_runs_job_key"), table_name="job_runs")
    op.drop_index(op.f("ix_job_runs_institution_id"), table_name="job_runs")
    op.drop_table("job_runs")
    op.drop_table("institutions")
