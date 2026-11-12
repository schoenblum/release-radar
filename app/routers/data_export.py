"""Full export of an institution's data, as JSON or XLSX (P8, Settings → Data).

This is the whole record for safekeeping, so it uses plain column names. The translated,
report-style export comes with the Data page at step 1.6. It holds personal data, which the
page says, and leaves out secrets by listing what is excluded per table below.
"""

import asyncio
import io
import json
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from openpyxl import Workbook
from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import require_admin
from app.models import (
    AuditLog,
    Checkpoint,
    CoreFieldConfig,
    CustomField,
    Institution,
    Measure,
    Reading,
    Release,
    ReleaseType,
    Researcher,
    ResearchField,
    ScoreProfile,
    ScoreProfileVersion,
    Unit,
    User,
    Vocabulary,
    VocabularyItem,
    Writer,
)
from app.services.audit import to_json

router = APIRouter(prefix="/settings/export", tags=["export"])

_ALWAYS_LEFT_OUT = {"field_versions"}
# Tables holding credentials are absent altogether: sessions, reset links, rate limits.
_TABLES: tuple[tuple[type, set[str]], ...] = (
    (Institution, set()),
    (User, {"password_hash", "token_version"}),
    (ResearchField, set()),
    (Unit, set()),
    (ReleaseType, set()),
    (Writer, set()),
    (Vocabulary, set()),
    (VocabularyItem, set()),
    (Researcher, set()),
    (Checkpoint, set()),
    (Measure, set()),
    (CoreFieldConfig, set()),
    (CustomField, set()),
    (Release, set()),
    (Reading, set()),
    (ScoreProfile, set()),
    (ScoreProfileVersion, set()),
    (AuditLog, set()),
)


async def _collect(db: AsyncSession, institution_id: Any) -> dict[str, list[dict[str, Any]]]:
    tables: dict[str, list[dict[str, Any]]] = {}
    for model, excluded in _TABLES:
        scope = model.id if model is Institution else model.institution_id
        keys = [
            attribute.key
            for attribute in inspect(model).column_attrs
            if attribute.key not in excluded | _ALWAYS_LEFT_OUT
        ]
        rows = await db.scalars(select(model).where(scope == institution_id))
        tables[model.__tablename__] = [
            {key: to_json(getattr(row, key)) for key in keys} for row in rows
        ]
    return tables


def _to_xlsx(tables: dict[str, list[dict[str, Any]]]) -> bytes:
    workbook = Workbook(write_only=False)
    workbook.remove(workbook.active)
    for name, rows in tables.items():
        sheet = workbook.create_sheet(name[:31])
        if not rows:
            continue
        columns = list(rows[0])
        sheet.append(columns)
        for row_number, row in enumerate(rows, start=2):
            for column_number, column in enumerate(columns, start=1):
                value = row[column]
                if isinstance(value, dict | list):
                    value = json.dumps(value, ensure_ascii=False)
                cell = sheet.cell(row=row_number, column=column_number, value=value)
                # Text starting with "=" must stay text, never run as a formula.
                if isinstance(value, str):
                    cell.data_type = "s"
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


@router.get("")
async def export_everything(
    file_format: str = Query(default="json", alias="format"),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    if file_format not in ("json", "xlsx"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="field_invalid")
    tables = await _collect(db, admin.institution_id)
    # The date people see on the file is their own, not UTC's.
    timezone = await db.scalar(
        select(Institution.timezone).where(Institution.id == admin.institution_id)
    )
    stamp = datetime.now(ZoneInfo(timezone)).strftime("%Y%m%d")
    if file_format == "json":
        content = json.dumps(tables, ensure_ascii=False, indent=2).encode("utf-8")
        media_type = "application/json"
    else:
        content = await asyncio.to_thread(_to_xlsx, tables)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="release_radar_{stamp}.{file_format}"'
        },
    )
