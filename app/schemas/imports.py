"""Bodies of the import API. ``frontend/src/api/types.ts`` mirrors these."""

from uuid import UUID

from pydantic import BaseModel, Field

# The workbooks are small (about 100 KB each); this keeps a wrong file from filling memory.
_MAX_BASE64 = 14_000_000


class UploadedFile(BaseModel):
    name: str = Field(max_length=255)
    # The file's bytes, base64-encoded: a JSON body needs no multipart parser.
    content: str = Field(max_length=_MAX_BASE64)


class PersonalFieldOwners(BaseModel):
    """Who owns each personal field seeded from the workbook. None: not imported."""

    bitly: UUID | None = None
    pitches: UUID | None = None
    request_received: UUID | None = None


class WorkbookImportRequest(BaseModel):
    release_list: UploadedFile
    intake: UploadedFile
    owners: PersonalFieldOwners = PersonalFieldOwners()
    # False: a dry run, which changes nothing and says what an import would do.
    commit: bool = False
    language: str = Field("en", pattern="^(en|ja)$")


class ImportCount(BaseModel):
    label: str
    count: int


class WorkbookImportResult(BaseModel):
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
