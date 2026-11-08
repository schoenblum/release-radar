"""Bodies of the Writers page API. ``frontend/src/api/types.ts`` mirrors these."""

from uuid import UUID

from pydantic import BaseModel


class WriterMonthRow(BaseModel):
    # None for the releases that have no writer yet.
    writer_id: UUID | None
    name_en: str | None
    name_ja: str | None
    is_active: bool
    counts: list[int]
    total: int


class WriterMonthly(BaseModel):
    academic_year: int
    # Every year with releases, and the current one, newest first.
    academic_years: list[int]
    # The months of the year in order, as YYYY-MM.
    months: list[str]
    rows: list[WriterMonthRow]
    totals: list[int]
    total: int
    # Releases without a release date, which no month counts yet.
    undated: int
