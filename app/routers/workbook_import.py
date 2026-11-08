"""Import of the old workbook (BRIEF step 1.8): admins only, a dry run first, then the import.

The files travel in the request and are never stored. The report comes back in the answer,
in Markdown and CSV, for the browser to offer as downloads: it names people, so it is not
kept on the server either.
"""

import base64
import binascii
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import require_admin
from app.models import Institution, User
from app.schemas.imports import ImportCount, WorkbookImportRequest, WorkbookImportResult
from app.services.workbook_import import importer, sheets

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

    now = datetime.now(ZoneInfo(timezone))
    language = request.language
    kind = "import" if request.commit else "dry_run"
    return WorkbookImportResult(
        committed=request.commit,
        counts=report.counts,
        summary=[
            ImportCount(label=label, count=count) for label, count in report.summary(language)
        ],
        levels=report.level_counts(),
        markdown=report.to_markdown(
            language,
            committed=request.commit,
            when=now.strftime("%Y-%m-%d %H:%M"),
            who=who,
        ),
        csv=report.to_csv(language),
        filename=f"release_radar_{kind}_{now.strftime('%Y%m%d_%H%M')}",
    )
