"""The Writers page (R7.7.1): releases per writer, by month of an academic year or by academic
year, for everyone signed in.

Counts only (R7.7.2). The export holds the same table as the page.
"""

import asyncio
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.i18n import t
from app.models import Institution, User
from app.schemas.writers import WriterCountRow, WriterCounts
from app.services import release_export, release_filters, writer_counts
from app.services.readings import today_in
from app.services.release_export import Table

router = APIRouter(prefix="/writers", tags=["writers"])

_MEDIA_TYPES = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "csv": "text/csv; charset=utf-8",
}


async def _counts(
    db: AsyncSession, institution: Institution, year: int | None, all_years: bool
) -> writer_counts.Counts:
    today = today_in(institution.timezone)
    if all_years:
        return await writer_counts.yearly_counts(db, institution, today)
    if year is None:
        year = writer_counts.current_academic_year(institution, today)
    return await writer_counts.monthly_counts(db, institution, year)


def _column_keys(counts: writer_counts.Counts) -> list[str]:
    if counts.period == "month":
        return [month.strftime("%Y-%m") for month in counts.columns]
    return [str(year) for year in counts.columns]


@router.get("/counts", response_model=WriterCounts)
async def writer_count_table(
    academic_year: int | None = Query(None, ge=1900, le=2999),
    all_years: bool = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WriterCounts:
    institution = await db.get(Institution, user.institution_id)
    counts = await _counts(db, institution, academic_year, all_years)
    current = writer_counts.current_academic_year(institution, today_in(institution.timezone))
    years = set(await release_filters.academic_years(db, institution)) | {current}
    return WriterCounts(
        period=counts.period,
        academic_year=counts.academic_year,
        academic_years=sorted(years, reverse=True),
        columns=_column_keys(counts),
        rows=[
            WriterCountRow(
                writer_id=row.writer_id,
                name_en=row.name_en,
                name_ja=row.name_ja,
                is_active=row.is_active,
                counts=row.counts,
                total=row.total,
            )
            for row in counts.rows
        ],
        totals=counts.totals,
        total=counts.total,
        undated=counts.undated,
    )


def _table(counts: writer_counts.Counts, language: str) -> Table:
    if counts.period == "month":
        # Machine-readable in both languages, so a file sorts and parses.
        headers = _column_keys(counts)
    else:
        headers = [t(language, "export.readme.academic_year", year=year) for year in counts.columns]
    table = Table(
        headers=[
            t(language, "writers_export.writer"),
            *headers,
            t(language, "writers_export.total"),
        ]
    )
    for row in writer_counts.sort_rows(counts.rows, language):
        name = row.name(language) or t(language, "writers_export.no_writer")
        table.rows.append([name, *row.counts, row.total])
    table.footer = [t(language, "writers_export.total"), *counts.totals, counts.total]
    return table


def _read_me(counts: writer_counts.Counts, language: str, when: datetime, who: str) -> list[str]:
    if counts.period == "month":
        first, last = counts.columns[0], counts.columns[-1]
        scope = t(
            language,
            "writers_export.readme.year",
            year=counts.academic_year,
            first=first.strftime("%Y-%m"),
            last=last.strftime("%Y-%m"),
        )
    else:
        scope = t(
            language,
            "writers_export.readme.all_years",
            first=t(language, "export.readme.academic_year", year=counts.columns[0]),
            last=t(language, "export.readme.academic_year", year=counts.columns[-1]),
        )
    lines = [
        t(language, "writers_export.readme.title"),
        t(language, "export.readme.exported", when=when.strftime("%Y-%m-%d %H:%M"), who=who),
        scope,
        "",
        t(language, "writers_export.readme.counting"),
        t(language, "writers_export.readme.totals"),
    ]
    if counts.undated:
        lines.append(t(language, "writers_export.readme.undated", count=counts.undated))
    lines += ["", t(language, "writers_export.readme.personal")]
    return lines


@router.get("/counts/export")
async def export_writer_counts(
    academic_year: int | None = Query(None, ge=1900, le=2999),
    all_years: bool = False,
    file_format: Literal["xlsx", "csv"] = Query("xlsx", alias="format"),
    language: Literal["en", "ja"] = Query("en"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    institution = await db.get(Institution, user.institution_id)
    counts = await _counts(db, institution, academic_year, all_years)
    table = _table(counts, language)
    now = datetime.now(ZoneInfo(institution.timezone))
    if file_format == "csv":
        content = release_export.to_csv(table)
    else:
        readme = _read_me(counts, language, now, user.full_name or user.email)
        content = await asyncio.to_thread(
            release_export.to_xlsx,
            (t(language, "writers_export.sheet"), table),
            {},
            (t(language, "export.sheets.readme"), readme),
        )
    scope = "all_years" if counts.academic_year is None else str(counts.academic_year)
    filename = f"release_radar_writers_{scope}_{now.strftime('%Y%m%d')}.{file_format}"
    return Response(
        content=content,
        media_type=_MEDIA_TYPES[file_format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
