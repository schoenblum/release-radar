"""The institution that owns all data. Exactly one row in v1 (R5.2.1).

Step 1.1 creates only what the skeleton needs. Step 1.2 adds the remaining
fields of BRIEF section 6.1.
"""

import uuid

from sqlalchemy import CheckConstraint, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import Timestamped


class Institution(Timestamped, Base):
    __tablename__ = "institutions"
    __table_args__ = (
        CheckConstraint("ay_start_month BETWEEN 1 AND 12", name="ay_start_month_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ja: Mapped[str | None] = mapped_column(String(255), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Tokyo")
    ay_start_month: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    settings: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
