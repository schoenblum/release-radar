"""Export from the Data page (R7.6.2): the view on screen, or everything, as XLSX or CSV.

Anyone signed in may export what they can see (viewers included, §3.1). Removed releases are
left out. The rows follow the order on screen when the page sends it, since the grid sorts
by itself; the rest come newest first.
"""

import asyncio
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.i18n import t
from app.models import Institution, Release, Researcher, ResearchField, Unit, User, Writer
from app.routers.releases import NEWEST_FIRST
from app.schemas.releases import ReleaseExportFilters, ReleaseExportRequest
from app.services import release_export, release_filters
from app.services.release_filters import ReleaseFilters

router = APIRouter(tags=["releases"])

_MEDIA_TYPES = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "csv": "text/csv; charset=utf-8",
}


def _filters(sent: ReleaseExportFilters | None) -> ReleaseFilters:
    if sent is None:
        return ReleaseFilters()
    return ReleaseFilters(
        view=sent.view,
        academic_year=sent.academic_year,
        field_id=sent.field_id,
        unit_id=sent.unit_id,
        researcher_id=sent.researcher_id,
        writer_id=sent.writer_id,
        search=sent.q,
    )


async def _describe(
    db: AsyncSession, institution: Institution, filters: ReleaseFilters, language: str
) -> str:
    """The filters in words, for the Read me sheet."""

    def named(en: str | None, ja: str | None) -> str:
        return (language == "ja" and ja) or en or ""

    parts = [t(language, f"export.readme.view_{filters.view}")]
    if filters.academic_year is not None:
        parts.append(t(language, "export.values.academic_year", year=filters.academic_year))
    lookups: list[tuple[Any, Any, Any]] = [
        (ResearchField, filters.field_id, lambda row: named(row.name_en, row.name_ja)),
        (Unit, filters.unit_id, lambda row: named(row.name_en, row.name_ja)),
        (Researcher, filters.researcher_id, lambda row: named(row.name, row.name_ja)),
        (Writer, filters.writer_id, lambda row: named(row.display_name_en, row.display_name_ja)),
    ]
    for model, wanted, label in lookups:
        if wanted is None:
            continue
        row = await db.scalar(
            select(model).where(model.id == wanted, model.institution_id == institution.id)
        )
        if row is not None:
            parts.append(label(row))
    words = release_filters.search_words(filters.search)
    if words:
        parts.append(t(language, "export.readme.search", text=" ".join(words)))
    return t(language, "export.readme.separator").join(parts)


@router.post("/releases/export")
async def export_releases(
    request: ReleaseExportRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    institution = await db.get(Institution, user.institution_id)
    language = request.language
    filters = _filters(request.filters)
    writer_id = await release_filters.own_writer_id(db, user)
    releases = list(
        await db.scalars(
            select(Release)
            .where(*release_filters.conditions(institution, filters, writer_id))
            .order_by(*NEWEST_FIRST)
        )
    )
    if request.order:
        place = {release_id: index for index, release_id in enumerate(request.order)}
        # Stable, so what the page did not send keeps its newest-first order after the rest.
        releases.sort(key=lambda release: place.get(release.id, len(place)))

    table = await release_export.release_table(db, institution, releases, language)
    now = datetime.now(ZoneInfo(institution.timezone))
    stamp = now.strftime("%Y%m%d")
    if request.file_format == "csv":
        content = release_export.to_csv(table)
    else:
        scope = (
            await _describe(db, institution, filters, language)
            if request.filters is not None
            else None
        )
        readme = release_export.read_me(
            language,
            when=now,
            who=user.full_name or user.email,
            count=len(releases),
            scope=scope,
            start_month=institution.ay_start_month,
        )
        lists = await release_export.list_tables(db, institution, language)
        content = await asyncio.to_thread(
            release_export.to_xlsx,
            (t(language, "export.sheets.releases"), table),
            lists,
            (t(language, "export.sheets.readme"), readme),
        )
    filename = f"release_radar_releases_{stamp}.{request.file_format}"
    return Response(
        content=content,
        media_type=_MEDIA_TYPES[request.file_format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
