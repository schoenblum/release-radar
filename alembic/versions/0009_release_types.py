"""release types (R6.4.1): the list, each release's type, and the institution's default

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-09 00:00:00.000000

Adds the list with EurekAlert's eleven categories for every institution that exists, makes
Peer-reviewed publication the default, and gives every existing release that type, as the
brief sets for imported releases. Bulk SQL, so the backfill is not in the audit log: it is
the starting value, like a new column's default. Then a settings row puts the field right
after the field (STEM/HSS) on forms. The downgrade drops all of it, types chosen since
included.
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

KEY = "release_type"
DEFAULT = "peer_reviewed"
# A copy of app/seeds.py and the catalogue as they are today: a migration must not change
# when they do.
TYPES = (
    ("peer_reviewed", "Peer-reviewed publication", "査読付き論文",
     ["Peer-reviewed publications", "Peer-reviewed", "Paper"]),
    ("reports_proceedings", "Reports and proceedings", "報告書・会議録",
     ["Reports and proceedings", "Report", "Proceedings"]),
    ("business", "Business announcement", "ビジネスに関する発表",
     ["Business announcements", "Business"]),
    ("meeting", "Meeting announcement", "会議の告知", ["Meeting announcements", "Meeting"]),
    ("grant_award", "Grant and award announcement", "助成・受賞の発表",
     ["Grant and award announcements", "Grant", "Award"]),
    ("book", "Book announcement", "書籍の発表", ["Book announcements", "Book"]),
    ("multimedia", "Multimedia release", "マルチメディアリリース", ["Multimedia"]),
    ("media_advisory", "Media advisory", "取材案内", ["Advisory"]),
    ("feature", "Feature story", "特集記事", ["Feature stories", "Feature"]),
    ("article_highlight", "Article highlight", "論文ハイライト", ["Article highlights"]),
    ("press_summary", "Press summary", "プレスサマリー", ["Press summaries"]),
)  # fmt: skip


def _create_schema() -> None:
    op.create_table(
        "release_types",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("name_en", sa.String(length=255), nullable=False),
        sa.Column("name_ja", sa.String(length=255), nullable=True),
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
        sa.Column(
            "field_versions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_release_types_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_release_types_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
            name=op.f("fk_release_types_updated_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_release_types")),
        sa.UniqueConstraint("institution_id", "key", name="uq_release_types_key"),
    )
    op.create_index(
        op.f("ix_release_types_institution_id"), "release_types", ["institution_id"], unique=False
    )
    op.add_column("institutions", sa.Column("default_release_type_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        op.f("fk_institutions_default_release_type_id_release_types"),
        "institutions",
        "release_types",
        ["default_release_type_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.add_column("releases", sa.Column("release_type_id", sa.UUID(), nullable=True))
    op.create_index(
        op.f("ix_releases_release_type_id"), "releases", ["release_type_id"], unique=False
    )
    op.create_foreign_key(
        op.f("fk_releases_release_type_id_release_types"),
        "releases",
        "release_types",
        ["release_type_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def _seed_and_backfill(connection: sa.Connection) -> None:
    institutions = connection.execute(sa.text("SELECT id FROM institutions")).scalars().all()
    for institution_id in institutions:
        default_id = None
        for position, (key, name_en, name_ja, aliases) in enumerate(TYPES):
            type_id = connection.execute(
                sa.text(
                    "INSERT INTO release_types (id, institution_id, key, name_en, name_ja, "
                    "aliases, position, is_active) VALUES (gen_random_uuid(), :institution, "
                    ":key, :name_en, :name_ja, CAST(:aliases AS jsonb), :position, true) "
                    "RETURNING id"
                ),
                {
                    "institution": institution_id,
                    "key": key,
                    "name_en": name_en,
                    "name_ja": name_ja,
                    "aliases": json.dumps(aliases, ensure_ascii=False),
                    "position": position,
                },
            ).scalar_one()
            if key == DEFAULT:
                default_id = type_id
        connection.execute(
            sa.text("UPDATE institutions SET default_release_type_id = :type WHERE id = :id"),
            {"type": default_id, "id": institution_id},
        )
        connection.execute(
            sa.text("UPDATE releases SET release_type_id = :type WHERE institution_id = :id"),
            {"type": default_id, "id": institution_id},
        )


def _form_row(connection: sa.Connection) -> None:
    """Right after the field (STEM/HSS), as in app/seeds.py, renumbering the rest."""
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
        place = keys.index("field") + 1 if "field" in keys else len(fields)
        fields.insert(place, (new_id, KEY))
        for position, (row_id, _) in enumerate(fields):
            connection.execute(
                sa.text("UPDATE core_field_configs SET position = :position WHERE id = :id"),
                {"position": position, "id": row_id},
            )


def upgrade() -> None:
    _create_schema()
    connection = op.get_bind()
    _seed_and_backfill(connection)
    _form_row(connection)


def downgrade() -> None:
    op.get_bind().execute(sa.text("DELETE FROM core_field_configs WHERE key = :key"), {"key": KEY})
    op.drop_constraint(
        op.f("fk_releases_release_type_id_release_types"), "releases", type_="foreignkey"
    )
    op.drop_index(op.f("ix_releases_release_type_id"), table_name="releases")
    op.drop_column("releases", "release_type_id")
    op.drop_constraint(
        op.f("fk_institutions_default_release_type_id_release_types"),
        "institutions",
        type_="foreignkey",
    )
    op.drop_column("institutions", "default_release_type_id")
    op.drop_index(op.f("ix_release_types_institution_id"), table_name="release_types")
    op.drop_table("release_types")
