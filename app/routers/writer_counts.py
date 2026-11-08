"""The Writers page (R7.7.1): releases per writer and month, for everyone signed in.

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
from app.schemas.writers import WriterMonthly, WriterMonthRow
from app.services import release_export, release_filters, writer_counts
from app.services.readings import today_in
from app.services.release_export import Table

router = APIRouter(prefix="/writers", tags=["writers"])

_MEDIA_TYPES = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "csv": "text/csv; charset=utf-8",
}


async def _counts(
    db: AsyncSession, institution: Institution, year: int | None
) -> writer_counts.MonthlyCounts:
    if year is None:
        year = writer_counts.current_academic_year(institution, today_in(institution.timezone))
    return await writer_counts.monthly_counts(db, institution, year)


@router.get("/monthly", response_model=WriterMonthly)
async def monthly(
    academic_year: int | None = Query(None, ge=1900, le=2999),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WriterMonthly:
    institution = await db.get(Institution, user.institution_id)
    counts = await _counts(db, institution, academic_year)
    current = writer_counts.current_academic_year(institution, today_in(institution.timezone))
    years = set(await release_filters.academic_years(db, institution)) | {current}
    return WriterMonthly(
        academic_year=counts.academic_year,
        academic_years=sorted(years, reverse=True),
        months=[month.strftime("%Y-%m") for month in counts.months],
        rows=[
            WriterMonthRow(
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


def _table(counts: writer_counts.MonthlyCounts, language: str) -> Table:
    table = Table(
        headers=[
            t(language, "writers_export.writer"),
            *[month.strftime("%Y-%m") for month in counts.months],
            t(language, "writers_export.total"),
        ]
    )
    for row in writer_counts.sort_rows(counts.rows, language):
        name = row.name(language) or t(language, "writers_export.no_writer")
        table.rows.append([name, *row.counts, row.total])
    table.footer = [t(language, "writers_export.total"), *counts.totals, counts.total]
    return table


def _read_me(
    counts: writer_counts.MonthlyCounts, language: str, when: datetime, who: str
) -> list[str]:
    first, last = counts.months[0], counts.months[-1]
    lines = [
        t(language, "writers_export.readme.title"),
        t(language, "export.readme.exported", when=when.strftime("%Y-%m-%d %H:%M"), who=who),
        t(
            language,
            "writers_export.readme.year",
            year=counts.academic_year,
            first=first.strftime("%Y-%m"),
            last=last.strftime("%Y-%m"),
        ),
        "",
        t(language, "writers_export.readme.counting"),
        t(language, "writers_export.readme.totals"),
    ]
    if counts.undated:
        lines.append(t(language, "writers_export.readme.undated", count=counts.undated))
    lines += ["", t(language, "writers_export.readme.personal")]
    return lines


@router.get("/monthly/export")
async def export_monthly(
    academic_year: int | None = Query(None, ge=1900, le=2999),
    file_format: Literal["xlsx", "csv"] = Query("xlsx", alias="format"),
    language: Literal["en", "ja"] = Query("en"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    institution = await db.get(Institution, user.institution_id)
    counts = await _counts(db, institution, academic_year)
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
    filename = (
        f"release_radar_writers_{counts.academic_year}_{now.strftime('%Y%m%d')}.{file_format}"
    )
    return Response(
        content=content,
        media_type=_MEDIA_TYPES[file_format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
