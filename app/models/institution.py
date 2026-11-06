"""The institution that owns all data. Exactly one row in v1 (R5.2.1)."""

from sqlalchemy import BigInteger, CheckConstraint, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import Audited, FieldVersioned, Timestamped, UuidKeyed

# The view each role lands on: "mine" and "all" are the two views of the Data page
# (D30). "mine" falls back to "all" for someone with no writer entry (step 1.6).
DEFAULT_LANDING_PAGES = {"admin": "mine", "editor": "mine", "viewer": "all"}
DEFAULT_EA_URL_PATTERN = r"^https://www\.eurekalert\.org/news-releases/\d+$"
DEFAULT_RELEASE_CODE_PATTERN = "AY{yyyy}-{nn}"
DEFAULT_MAJOR_OUTLET_THRESHOLD = 1_000_000


class Institution(UuidKeyed, Timestamped, Audited, FieldVersioned, Base):
    __tablename__ = "institutions"
    __table_args__ = (
        CheckConstraint("ay_start_month BETWEEN 1 AND 12", name="ay_start_month_range"),
    )

    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ja: Mapped[str | None] = mapped_column(String(255), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Tokyo")
    ay_start_month: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    # The host of the institution's news site. Website views apply only to releases
    # on exactly this host, which is what excludes an older site (D23).
    website_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ea_url_pattern: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=DEFAULT_EA_URL_PATTERN,
        server_default=DEFAULT_EA_URL_PATTERN,
    )
    release_code_pattern: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=DEFAULT_RELEASE_CODE_PATTERN,
        server_default=DEFAULT_RELEASE_CODE_PATTERN,
    )
    landing_pages: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=lambda: dict(DEFAULT_LANDING_PAGES),
        server_default=text("""'{"admin": "mine", "editor": "mine", "viewer": "all"}'::jsonb"""),
    )
    major_outlet_threshold: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=DEFAULT_MAJOR_OUTLET_THRESHOLD,
        server_default=str(DEFAULT_MAJOR_OUTLET_THRESHOLD),
    )
    # Sent to Crossref as the polite contact (step 1.4). An office address, not a person's.
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    settings: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
