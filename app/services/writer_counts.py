"""Releases per writer, by month of one academic year or by academic year (R7.7.1).

Counts only, by release date: no views, scores or pickups (R7.7.2). A release without a date
belongs to no month or year yet, and a removed release is not counted.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import case, extract, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Institution, Release, Writer
from app.services.release_codes import academic_year

Period = Literal["month", "year"]


@dataclass
class WriterRow:
    """One writer's counts, one per column. ``writer_id`` is None for releases with no writer."""

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
class Counts:
    period: Period
    # The first day of each month, or each academic year, in order.
    columns: list[date] | list[int]
    # The year shown month by month; None when the columns are years.
    academic_year: int | None = None
    rows: list[WriterRow] = field(default_factory=list)
    # Releases with no release date yet, which no column counts.
    undated: int = 0

    @property
    def totals(self) -> list[int]:
        return [sum(row.counts[place] for row in self.rows) for place in range(len(self.columns))]

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


def current_academic_year(institution: Institution, today: date) -> int:
    return academic_year(today, institution.ay_start_month)


def _in_institution(institution: Institution) -> list[Any]:
    return [Release.institution_id == institution.id, Release.deleted_at.is_(None)]


async def _rows(
    db: AsyncSession, institution: Institution, counts: dict[UUID | None, list[int]], width: int
) -> list[WriterRow]:
    # Everyone still writing, and anyone who wrote in these columns even if they have left since.
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
            counts=counts.get(writer.id, [0] * width),
        )
        for writer in writers
    ]
    if None in counts:
        rows.append(
            WriterRow(
                writer_id=None, name_en=None, name_ja=None, is_active=True, counts=counts[None]
            )
        )
    return sort_rows(rows, "en")


async def _undated(db: AsyncSession, institution: Institution) -> int:
    number = await db.scalar(
        select(func.count()).where(*_in_institution(institution), Release.release_date.is_(None))
    )
    return number or 0


async def monthly_counts(db: AsyncSession, institution: Institution, year: int) -> Counts:
    months = months_of(year, institution.ay_start_month)
    start = months[0]
    end = date(start.year + 1, start.month, 1)
    place = {(month.year, month.month): index for index, month in enumerate(months)}
    release_year = extract("year", Release.release_date)
    release_month = extract("month", Release.release_date)

    counted = await db.execute(
        select(Release.writer_id, release_year, release_month, func.count())
        .where(
            *_in_institution(institution),
            Release.release_date >= start,
            Release.release_date < end,
        )
        .group_by(Release.writer_id, release_year, release_month)
    )
    counts: dict[UUID | None, list[int]] = {}
    for writer_id, number_year, number_month, number in counted:
        row = counts.setdefault(writer_id, [0] * 12)
        row[place[(int(number_year), int(number_month))]] += number

    return Counts(
        period="month",
        columns=months,
        academic_year=year,
        rows=await _rows(db, institution, counts, 12),
        undated=await _undated(db, institution),
    )


async def yearly_counts(db: AsyncSession, institution: Institution, today: date) -> Counts:
    """Every academic year from the first release to the last, oldest first."""
    start_month = institution.ay_start_month
    release_year = extract("year", Release.release_date) - case(
        (extract("month", Release.release_date) < start_month, 1), else_=0
    )
    counted = (
        await db.execute(
            select(Release.writer_id, release_year, func.count())
            .where(*_in_institution(institution), Release.release_date.is_not(None))
            .group_by(Release.writer_id, release_year)
        )
    ).all()
    years_seen = [int(year) for _, year, _ in counted]
    years = (
        list(range(min(years_seen), max(years_seen) + 1))
        if years_seen
        else [current_academic_year(institution, today)]
    )
    place = {year: index for index, year in enumerate(years)}
    counts: dict[UUID | None, list[int]] = {}
    for writer_id, year, number in counted:
        counts.setdefault(writer_id, [0] * len(years))[place[int(year)]] += number

    return Counts(
        period="year",
        columns=years,
        rows=await _rows(db, institution, counts, len(years)),
        undated=await _undated(db, institution),
    )
