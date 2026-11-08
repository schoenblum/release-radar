"""Bodies of the Writers page API. ``frontend/src/api/types.ts`` mirrors these."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class WriterCountRow(BaseModel):
    # None for the releases that have no writer yet.
    writer_id: UUID | None
    name_en: str | None
    name_ja: str | None
    is_active: bool
    counts: list[int]
    total: int


class WriterCounts(BaseModel):
    # Month by month for one academic year, or year by year for all of them.
    period: Literal["month", "year"]
    # The year shown month by month; None for all years.
    academic_year: int | None
    # Every year with releases, and the current one, newest first.
    academic_years: list[int]
    # The columns in order: YYYY-MM for months, YYYY for academic years.
    columns: list[str]
    rows: list[WriterCountRow]
    totals: list[int]
    total: int
    # Releases without a release date, which no column counts yet.
    undated: int
