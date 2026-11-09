"""The import history (Daniel, 2026-11-08): every check and import, with its report, so what
needs correcting can be found again later. The files themselves are not kept."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ImportRun
from app.services.workbook_import.report import Report


async def save_run(
    db: AsyncSession,
    institution_id: uuid.UUID,
    user_id: uuid.UUID | None,
    *,
    committed: bool,
    file_names: list[str],
    report: Report,
) -> ImportRun:
    """Keep a run in its own transaction: after a check's rollback, or an import's commit."""
    run = ImportRun(
        institution_id=institution_id,
        kind=report.kind,
        user_id=user_id,
        committed=committed,
        file_names=file_names,
        counts=report.counts,
        entries=[entry.stored() for entry in report.entries],
    )
    db.add(run)
    await db.commit()
    return run


def report_of(run: ImportRun) -> Report:
    return Report.from_stored(run.counts, run.entries, run.kind)
