"""Bodies of the import API. ``frontend/src/api/types.ts`` mirrors these."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

# The workbooks are small (about 100 KB each); this keeps a wrong file from filling memory.
_MAX_BASE64 = 14_000_000


class UploadedFile(BaseModel):
    name: str = Field(max_length=255)
    # The file's bytes, base64-encoded: a JSON body needs no multipart parser.
    content: str = Field(max_length=_MAX_BASE64)


class ColumnChoiceIn(BaseModel):
    """What to do with a workbook column Release Radar doesn't know yet (Daniel, 2026-11-12):
    nothing, a shared field, or a private field for each chosen person."""

    key: str = Field(max_length=600)
    action: Literal["skip", "shared", "personal"] = "skip"
    field_type: Literal["integer", "number", "date", "text"] = "text"
    owners: list[UUID] = Field(default=[], max_length=100)


class WorkbookImportRequest(BaseModel):
    release_list: UploadedFile
    # Only for the first import: later ones take writers, units and fields from Settings.
    intake: UploadedFile | None = None
    columns: list[ColumnChoiceIn] = Field(default=[], max_length=200)
    # The catch-up before D1 (phase-2 brief §3.4): existing releases get only what is empty.
    fill_empty_only: bool = False
    # False: a dry run, which changes nothing and says what an import would do.
    commit: bool = False
    language: str = Field("en", pattern="^(en|ja)$")


class FeedbackImportRequest(BaseModel):
    """A Microsoft Forms export of the researcher feedback survey (R8.1.2)."""

    file: UploadedFile
    commit: bool = False
    language: str = Field("en", pattern="^(en|ja)$")


class ImportCount(BaseModel):
    label: str
    count: int


class ColumnFillOut(BaseModel):
    label: str
    # The owner's name for a private field; None for a shared one.
    owner: str | None


class ColumnOut(BaseModel):
    """A workbook column with no place of its own, and the fields it fills."""

    key: str
    heading: str
    group: str
    examples: list[str]
    suggested_type: str
    fills: list[ColumnFillOut]
    # A field remembered it from an earlier import.
    known: bool


class WorkbookImportResult(BaseModel):
    # In the import history, where its report can be downloaded again.
    run_id: UUID
    committed: bool
    counts: dict[str, int]
    # The counts in order, labelled in the request's language.
    summary: list[ImportCount]
    # Report entries by level: check (to look at), dash, info.
    levels: dict[str, int]
    markdown: str
    csv: str
    # A file name without extension, for the two report downloads.
    filename: str
    columns: list[ColumnOut] = []


class ImportRunOut(BaseModel):
    """One check or import, as the history lists it."""

    id: UUID
    # workbook or feedback.
    kind: str
    created_at: datetime
    committed: bool
    file_names: list[str]
    user_name: str | None
    counts: dict[str, int]
    # Report entries by level: check, dash, info.
    levels: dict[str, int]


ReportFormat = Literal["md", "csv"]
ImportKind = Literal["workbook", "feedback"]


class FeedbackItemOut(BaseModel):
    key: str
    question: str
    kind: str
    exclusive: bool
    external: bool
    label_en: str
    label_ja: str | None


class FeedbackResponseOut(BaseModel):
    """One researcher's answers, for the record's Researcher feedback section (office only)."""

    id: UUID
    source: str
    template_name: str
    submitted_at: datetime | None
    language: str | None
    respondent_name: str | None
    answers: dict
    other_texts: dict
    items: list[FeedbackItemOut]
