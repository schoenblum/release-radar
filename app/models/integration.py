"""Connections to outside services, such as Google Analytics (Settings → Integrations).

One row per institution and kind. The credential is Fernet-encrypted (R5.2.4), never
returned by the API, never logged, and recorded in the audit log only as "changed".
"""

from datetime import datetime

from sqlalchemy import DateTime, LargeBinary, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import FieldVersioned, Record

KIND_GA4 = "ga4"


class Integration(Record, FieldVersioned, Base):
    __tablename__ = "integrations"
    __table_args__ = (UniqueConstraint("institution_id", "kind", name="uq_integrations_kind"),)
    __audit_redact__ = frozenset({"credential"})
    __audit_expand__ = frozenset({"config"})
    # Clicking Test connection is not a change to the record.
    __audit_exclude__ = frozenset({"last_test_at", "last_test_result"})

    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    # Encrypted with FERNET_KEY. A key made on another install cannot be read here.
    credential: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    # What may be shown: for Google Analytics the property ID, the service account's
    # address and its project. Never anything secret.
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Daily fetches wait for a person's first Fetch now, so real data never arrives unasked.
    first_fetch_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_test_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # {"ok": bool, "code": str, "detail": str | None, "views": int | None, "date": str}
    last_test_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
