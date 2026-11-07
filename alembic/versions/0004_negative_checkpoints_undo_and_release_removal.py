"""negative checkpoints, reminder timing, undoing merges, removing releases

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-07 15:30:00.000000

Adds only. Checkpoints may now fall before the release date, so the check that refused a
negative offset goes.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(op.f("ck_checkpoints_offset_not_negative"), "checkpoints", type_="check")
    op.add_column(
        "checkpoints",
        sa.Column("remind_days_before", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_check_constraint(
        op.f("ck_checkpoints_remind_days_before_known"),
        "checkpoints",
        "remind_days_before IN (0, 1)",
    )
    op.add_column("releases", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "researchers",
        sa.Column("merge_details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("researchers", "merge_details")
    op.drop_column("releases", "deleted_at")
    op.drop_constraint(
        op.f("ck_checkpoints_remind_days_before_known"), "checkpoints", type_="check"
    )
    op.drop_column("checkpoints", "remind_days_before")
    # NOT VALID, so a checkpoint added before the release date is kept rather than lost.
    op.execute(
        "ALTER TABLE checkpoints ADD CONSTRAINT ck_checkpoints_offset_not_negative "
        "CHECK (offset_days >= 0) NOT VALID"
    )
