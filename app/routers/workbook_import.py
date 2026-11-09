"""Import of the old workbook (BRIEF step 1.8): admins only, a dry run first, then the import.

The files travel in the request and are not kept: once imported, the data lives here. Each
check and import is kept in the history with its report, which can be downloaded again later
in either language.
"""

import base64
import binascii
from datetime import datetime
from typing import Any, Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import require_admin
from app.models import ImportRun, Institution, User
from app.schemas.imports import (
    FeedbackImportRequest,
    ImportCount,
    ImportKind,
    ImportRunOut,
    ReportFormat,
    WorkbookImportRequest,
    WorkbookImportResult,
)
from app.services.feedback import importer as feedback_importer
from app.services.workbook_import import history, importer, sheets
from app.services.workbook_import.report import Report

router = APIRouter(prefix="/imports", tags=["imports"])


def _decode(content: str) -> bytes:
    try:
        return base64.b64decode(content, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, detail="import_not_a_workbook"
        ) from exc


@router.post("/workbook", response_model=WorkbookImportResult)
async def import_workbook(
    request: WorkbookImportRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Any:
    institution = await db.get(Institution, admin.institution_id)
    # Read now: a dry run's rollback expires what the session loaded.
    timezone, who = institution.timezone, admin.full_name or admin.email
    institution_id, admin_id = institution.id, admin.id
    files = importer.Files(
        release_list=_decode(request.release_list.content), intake=_decode(request.intake.content)
    )
    try:
        report = await importer.run_import(
            db, institution, admin, files, request.owners.model_dump()
        )
    except sheets.WorkbookProblem as problem:
        await db.rollback()
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": f"import_{problem.code}", **problem.details},
        )
    if request.commit:
        await db.commit()
    else:
        await db.rollback()
    run = await history.save_run(
        db,
        institution_id,
        admin_id,
        committed=request.commit,
        file_names=[request.release_list.name, request.intake.name],
        report=report,
    )

    return _result(run.id, report, request.commit, request.language, timezone, who)


def _result(
    run_id: UUID, report: Report, committed: bool, language: str, timezone: str, who: str
) -> WorkbookImportResult:
    now = datetime.now(ZoneInfo(timezone))
    return WorkbookImportResult(
        run_id=run_id,
        committed=committed,
        counts=report.counts,
        summary=[
            ImportCount(label=label, count=count) for label, count in report.summary(language)
        ],
        levels=report.level_counts(),
        markdown=report.to_markdown(
            language,
            committed=committed,
            when=now.strftime("%Y-%m-%d %H:%M"),
            who=who,
        ),
        csv=report.to_csv(language),
        filename=_filename(committed, now, report.kind),
    )


def _filename(committed: bool, when: datetime, kind: str = "workbook") -> str:
    what = "import" if committed else "dry_run"
    prefix = "" if kind == "workbook" else f"{kind}_"
    return f"release_radar_{prefix}{what}_{when.strftime('%Y%m%d_%H%M')}"


@router.post("/feedback", response_model=WorkbookImportResult)
async def import_feedback(
    request: FeedbackImportRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Researcher feedback from a Microsoft Forms export (R8.1.2): check first, then import.
    Re-runnable: responses already imported are found by the export's Id and left alone."""
    institution = await db.get(Institution, admin.institution_id)
    timezone, who = institution.timezone, admin.full_name or admin.email
    institution_id, admin_id = institution.id, admin.id
    content = _decode(request.file.content)
    try:
        report = await feedback_importer.run_import(db, institution, admin, content)
    except sheets.WorkbookProblem as problem:
        await db.rollback()
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": f"import_{problem.code}", **problem.details},
        )
    if request.commit:
        await db.commit()
    else:
        await db.rollback()
    run = await history.save_run(
        db,
        institution_id,
        admin_id,
        committed=request.commit,
        file_names=[request.file.name],
        report=report,
    )
    return _result(run.id, report, request.commit, request.language, timezone, who)


@router.get("", response_model=list[ImportRunOut])
async def import_history(
    kind: ImportKind | None = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[ImportRunOut]:
    query = (
        select(ImportRun, User.full_name, User.email)
        .outerjoin(User, User.id == ImportRun.user_id)
        .where(ImportRun.institution_id == admin.institution_id)
    )
    if kind is not None:
        query = query.where(ImportRun.kind == kind)
    rows = await db.execute(query.order_by(ImportRun.created_at.desc()).limit(50))
    return [
        ImportRunOut(
            id=run.id,
            kind=run.kind,
            created_at=run.created_at,
            committed=run.committed,
            file_names=run.file_names,
            user_name=full_name or email,
            counts=run.counts,
            levels=history.report_of(run).level_counts(),
        )
        for run, full_name, email in rows.all()
    ]


@router.get("/{run_id}/report")
async def import_report(
    run_id: UUID,
    file_format: ReportFormat = Query("md", alias="format"),
    language: Literal["en", "ja"] = Query("en"),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    run = await db.scalar(
        select(ImportRun).where(
            ImportRun.id == run_id, ImportRun.institution_id == admin.institution_id
        )
    )
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
    institution = await db.get(Institution, admin.institution_id)
    who = await db.get(User, run.user_id) if run.user_id else None
    when = run.created_at.astimezone(ZoneInfo(institution.timezone))
    report: Report = history.report_of(run)
    name = _filename(run.committed, when, run.kind)
    if file_format == "csv":
        return Response(
            content=report.to_csv(language).encode("utf-8-sig"),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{name}.csv"'},
        )
    markdown = report.to_markdown(
        language,
        committed=run.committed,
        when=when.strftime("%Y-%m-%d %H:%M"),
        who=(who.full_name or who.email) if who else "—",
    )
    return Response(
        content=markdown.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{name}.md"'},
    )
