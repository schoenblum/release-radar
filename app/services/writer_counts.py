"""Releases per writer and month of an academic year (R7.7.1).

Counts only, by release date: no views, scores or pickups (R7.7.2). A release without a date
belongs to no month yet, and a removed release is not counted.
"""

from dataclasses import dataclass, field
from datetime import date
from uuid import UUID

from sqlalchemy import extract, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Institution, Release, Writer
from app.services.release_codes import academic_year


@dataclass
class WriterRow:
    """One writer's counts, a month per place. ``writer_id`` is None for releases with no writer."""

    writer_id: UUID | None
    name_en: str | None
    name_ja: str | None
    is_active: bool
    counts: list[int]

    @property
    def total(self) -> int:
        return sum(self.counts)

    def name(self, language: str) -> str | None:
        return (language == "ja" and self.name_ja) or self.name_en


@dataclass
class MonthlyCounts:
    academic_year: int
    months: list[date]
    rows: list[WriterRow] = field(default_factory=list)
    # Releases with no release date yet, which no month can count.
    undated: int = 0

    @property
    def totals(self) -> list[int]:
        return [sum(row.counts[place] for row in self.rows) for place in range(len(self.months))]

    @property
    def total(self) -> int:
        return sum(row.total for row in self.rows)


def months_of(year: int, start_month: int) -> list[date]:
    """The first day of each month of the academic year, in order: April to March at Nagoya."""
    return [
        date(year + (start_month - 1 + offset) // 12, (start_month - 1 + offset) % 12 + 1, 1)
        for offset in range(12)
    ]


def sort_rows(rows: list[WriterRow], language: str) -> list[WriterRow]:
    """By name in the chosen language, with releases that have no writer last."""
    return sorted(
        rows, key=lambda row: (row.writer_id is None, (row.name(language) or "").casefold())
    )


async def monthly_counts(db: AsyncSession, institution: Institution, year: int) -> MonthlyCounts:
    months = months_of(year, institution.ay_start_month)
    start = months[0]
    end = date(start.year + 1, start.month, 1)
    place = {(month.year, month.month): index for index, month in enumerate(months)}

    counted = await db.execute(
        select(
            Release.writer_id,
            extract("year", Release.release_date),
            extract("month", Release.release_date),
            func.count(),
        )
        .where(
            Release.institution_id == institution.id,
            Release.deleted_at.is_(None),
            Release.release_date >= start,
            Release.release_date < end,
        )
        .group_by(
            Release.writer_id,
            extract("year", Release.release_date),
            extract("month", Release.release_date),
        )
    )
    counts: dict[UUID | None, list[int]] = {}
    for writer_id, release_year, release_month, number in counted:
        counts.setdefault(writer_id, [0] * 12)[place[(int(release_year), int(release_month))]] += (
            number
        )

    # Everyone still writing, and anyone who wrote in this year even if they have since left.
    writers = await db.scalars(
        select(Writer).where(
            Writer.institution_id == institution.id,
            or_(Writer.is_active.is_(True), Writer.id.in_([key for key in counts if key])),
        )
    )
    rows = [
        WriterRow(
            writer_id=writer.id,
            name_en=writer.display_name_en,
            name_ja=writer.display_name_ja,
            is_active=writer.is_active,
            counts=counts.get(writer.id, [0] * 12),
        )
        for writer in writers
    ]
    if None in counts:
        rows.append(
            WriterRow(
                writer_id=None, name_en=None, name_ja=None, is_active=True, counts=counts[None]
            )
        )

    undated = await db.scalar(
        select(func.count()).where(
            Release.institution_id == institution.id,
            Release.deleted_at.is_(None),
            Release.release_date.is_(None),
        )
    )
    return MonthlyCounts(
        academic_year=year, months=months, rows=sort_rows(rows, "en"), undated=undated or 0
    )


def current_academic_year(institution: Institution, today: date) -> int:
    return academic_year(today, institution.ay_start_month)
