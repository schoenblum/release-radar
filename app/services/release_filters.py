"""Which releases a view shows (R7.6.1): the Data page's filters and search.

The grid and the export use the same conditions, so a file holds exactly what the page shows.
The academic year comes from the release date and the institution's start month, never from
the code (D35).
"""

import unicodedata
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import Text, cast, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Institution, Release, Researcher, User, Writer
from app.services import crossref
from app.services.release_codes import academic_year

View = Literal["all", "mine"]

# More words than this say nothing new, and each one costs a condition.
_MAX_WORDS = 8


@dataclass(frozen=True)
class ReleaseFilters:
    view: View = "all"
    academic_year: int | None = None
    field_id: UUID | None = None
    unit_id: UUID | None = None
    researcher_id: UUID | None = None
    writer_id: UUID | None = None
    search: str | None = None

    @property
    def narrowed(self) -> bool:
        """Whether anything beyond the view itself is chosen."""
        return any(
            value is not None
            for value in (
                self.academic_year,
                self.field_id,
                self.unit_id,
                self.researcher_id,
                self.writer_id,
            )
        ) or bool(search_words(self.search))


def search_words(text: str | None) -> list[str]:
    """Full-width letters and spaces count as their plain forms, as typed with an IME."""
    if not text:
        return []
    return unicodedata.normalize("NFKC", text).split()[:_MAX_WORDS]


async def own_writer_id(db: AsyncSession, user: User) -> UUID | None:
    return await db.scalar(
        select(Writer.id).where(
            Writer.institution_id == user.institution_id, Writer.user_id == user.id
        )
    )


def _matches(word: str, institution_id: UUID) -> Any:
    """One word, anywhere a person would look for it, the researcher's names included."""
    researchers = select(Researcher.id).where(
        Researcher.institution_id == institution_id,
        or_(
            *(
                column.icontains(word, autoescape=True)
                for column in (
                    Researcher.name,
                    Researcher.name_ja,
                    Researcher.given_name,
                    Researcher.family_name,
                )
            )
        ),
    )
    doi = crossref.normalise_doi(word) or word.lower()
    return or_(
        *(
            column.icontains(word, autoescape=True)
            for column in (
                Release.code,
                Release.title,
                Release.title_ja,
                Release.journal,
                Release.paper_title,
                Release.also_featured,
                Release.notes,
                cast(Release.authors, Text),
            )
        ),
        Release.doi.icontains(doi, autoescape=True),
        Release.researcher_id.in_(researchers),
    )


def conditions(
    institution: Institution, filters: ReleaseFilters, own_writer: UUID | None
) -> list[Any]:
    """The WHERE clause for a view. Removed releases never show."""
    where: list[Any] = [Release.institution_id == institution.id, Release.deleted_at.is_(None)]
    if filters.view == "mine":
        # With no writer entry nothing is theirs, rather than everything without a writer.
        where.append(Release.writer_id == own_writer if own_writer else false())
    if filters.academic_year is not None:
        start = institution.ay_start_month
        where.append(Release.release_date >= date(filters.academic_year, start, 1))
        where.append(Release.release_date < date(filters.academic_year + 1, start, 1))
    for column, value in (
        (Release.field_id, filters.field_id),
        (Release.unit_id, filters.unit_id),
        (Release.researcher_id, filters.researcher_id),
        (Release.writer_id, filters.writer_id),
    ):
        if value is not None:
            where.append(column == value)
    where.extend(_matches(word, institution.id) for word in search_words(filters.search))
    return where


async def academic_years(db: AsyncSession, institution: Institution) -> list[int]:
    """Every academic year from the first release to the last, newest first."""
    first, last = (
        await db.execute(
            select(func.min(Release.release_date), func.max(Release.release_date)).where(
                Release.institution_id == institution.id, Release.deleted_at.is_(None)
            )
        )
    ).one()
    if first is None or last is None:
        return []
    start = institution.ay_start_month
    return list(range(academic_year(last, start), academic_year(first, start) - 1, -1))
