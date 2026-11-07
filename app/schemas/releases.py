"""Bodies of the release API. ``frontend/src/api/types.ts`` mirrors these."""

from datetime import date, datetime, time
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReadingOut(BaseModel):
    id: UUID
    measure_id: UUID
    measure_key: str
    value: float | None
    # What is stored: value, not_applicable or missing.
    state: str
    # What to show, which adds not_yet_due (R6.5.1).
    display_state: str
    source: str
    due_date: date | None
    remind_on: date | None
    note: str | None
    version: int
    entered_at: datetime | None


class ReleaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str | None
    title: str | None
    title_ja: str | None
    writer_id: UUID | None
    researcher_id: UUID | None
    researcher_name: str | None = None
    also_featured: str | None
    unit_id: UUID | None
    field_id: UUID | None
    doi: str | None
    journal: str | None
    paper_title: str | None
    publication_date: date | None
    authors: list[dict[str, Any]]
    embargoed: bool
    release_date: date | None
    # From the date, never from the code (D35).
    academic_year: int | None = None
    release_time_et: time | None
    ea_url: str | None
    website_url: str | None
    ea_top_page: bool
    ea_top_position: int | None
    notes: str | None
    custom_values: dict[str, Any]
    field_versions: dict[str, int]
    created_at: datetime
    updated_at: datetime
    readings: list[ReadingOut] = []
    # Saved, but worth a look (R7.5.8).
    warnings: list[str] = []
    # Required by Settings and still empty. Drafts are allowed to be incomplete (R7.5.6).
    missing_required: list[str] = []


class ReleasePage(BaseModel):
    items: list[ReleaseOut]
    total: int
    # Whether this person has a writer entry at all, which "mine" depends on.
    has_writer_entry: bool


class ReleaseCreate(BaseModel):
    """R7.5.6: a title or a DOI is enough. Everything else can follow."""

    title: str | None = None
    doi: str | None = None


class ReleaseCreated(ReleaseOut):
    # found, not_found or unavailable. Absent if there was no DOI to look up.
    crossref: str | None = None


class ReleaseSaved(BaseModel):
    field: str
    value: Any
    version: int
    release: ReleaseOut


class ReadingPatch(BaseModel):
    """Send ``value``, or ``state`` to set N/A or clear it, and the version last seen."""

    version: int
    value: Any = None
    state: Literal["value", "not_applicable", "missing"] | None = None
    note: str | None = None


class CustomValuePatch(BaseModel):
    version: int = 0
    value: Any = None
    state: Literal["value", "not_applicable", "missing"] | None = None


class CrossrefRefetch(BaseModel):
    # True overwrites what is there, as the refetch button does. False only fills gaps,
    # as when a DOI has just been entered on a release that already has paper details.
    overwrite: bool = True


class CrossrefRefetched(BaseModel):
    status: str
    release: ReleaseOut


class DoiLookup(BaseModel):
    doi: str


class DoiLookupOut(BaseModel):
    doi: str
    status: str
    journal: str | None
    paper_title: str | None
    publication_date: date | None
    authors: list[dict[str, Any]]


class DueItem(BaseModel):
    """Something this person is asked for (R7.5.1). Never called late or overdue (P5)."""

    kind: Literal["reading", "custom"]
    release_id: UUID
    release_code: str | None
    release_title: str | None
    due_date: date
    # False means it is coming up in the next few days.
    due_now: bool
    label_en: str
    label_ja: str | None
    version: int
    reading_id: UUID | None = None
    measure_key: str | None = None
    measure_unit: str | None = None
    field_key: str | None = None
    field_type: str | None = None


class HistoryEntry(BaseModel):
    at: datetime
    action: str
    # release or reading.
    entity: str
    # Which measure, for a reading.
    measure_key: str | None
    field: str | None
    old_value: Any
    new_value: Any
    # The researcher's name, where the value is an ID the screen has no list for.
    old_label: str | None = None
    new_label: str | None = None
    user_id: UUID | None
    user_name: str | None
    user_active: bool | None
