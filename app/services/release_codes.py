"""Release codes: assigned by the system, once, and never changed (D35).

A release gets the next free number of its date's academic year when that date is first
entered. Removed releases still hold their number, and gaps are not filled, so a code that
has ever pointed at a release never points at another one.

The year here is only for numbering. Everything else takes the year from the date, because a
date can later move to another academic year while its code stays.
"""

import re
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.institution import Institution
from app.models.release import Release

# Keeps two saves from taking the same number. Only code assignment uses this class of lock.
_LOCK_CLASS = 0x5252


def academic_year(day: date, start_month: int) -> int:
    return day.year if day.month >= start_month else day.year - 1


def _numbering(pattern: str, year: int) -> re.Pattern[str]:
    before, after = pattern.replace("{yyyy}", str(year)).split("{nn}")
    return re.compile(f"^{re.escape(before)}(\\d+){re.escape(after)}$")


def format_code(pattern: str, year: int, number: int) -> str:
    return pattern.replace("{yyyy}", str(year)).replace("{nn}", f"{number:02d}")


async def next_code(db: AsyncSession, institution: Institution, day: date) -> str:
    """The next free code for this date. Holds a lock until the transaction ends."""
    await db.execute(
        select(func.pg_advisory_xact_lock(_LOCK_CLASS, func.hashtext(str(institution.id))))
    )
    year = academic_year(day, institution.ay_start_month)
    numbering = _numbering(institution.release_code_pattern, year)
    codes = await db.scalars(
        select(Release.code).where(
            Release.institution_id == institution.id, Release.code.is_not(None)
        )
    )
    numbers = [int(found.group(1)) for code in codes if (found := numbering.match(code))]
    return format_code(institution.release_code_pattern, year, max(numbers, default=0) + 1)


async def assign_code(db: AsyncSession, release: Release, institution: Institution) -> None:
    """Give a release its code once it has a date. One that has a code keeps it."""
    if release.code is None and release.release_date is not None:
        release.code = await next_code(db, institution, release.release_date)
