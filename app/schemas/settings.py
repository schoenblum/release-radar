"""Response bodies for Settings. ``frontend/src/api/types.ts`` mirrors these."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class InstitutionOut(_Out):
    id: UUID
    name_en: str
    name_ja: str | None
    timezone: str
    ay_start_month: int
    website_domain: str | None
    release_code_pattern: str
    landing_pages: dict[str, str]
    contact_email: str | None
    field_versions: dict[str, int]


class ResearchFieldOut(_Out):
    id: UUID
    name_en: str
    name_ja: str | None
    scope_note: str | None
    is_active: bool
    field_versions: dict[str, int]


class UnitOut(_Out):
    id: UUID
    key: str
    name_en: str
    name_ja: str | None
    short_label: str | None
    unit_type: str | None
    aliases: list[str]
    default_field_id: UUID | None
    is_active: bool
    field_versions: dict[str, int]


class WriterOut(_Out):
    id: UUID
    display_name_en: str
    display_name_ja: str | None
    full_name: str | None
    user_id: UUID | None
    is_active: bool
    field_versions: dict[str, int]


class VocabularyOut(_Out):
    id: UUID
    key: str
    name_en: str
    name_ja: str | None
    is_active: bool
    field_versions: dict[str, int]


class VocabularyItemOut(_Out):
    id: UUID
    vocabulary_id: UUID
    key: str
    label_en: str
    label_ja: str | None
    aliases: list[str]
    position: int
    is_active: bool
    field_versions: dict[str, int]


class CreateEntry(BaseModel):
    values: dict[str, Any]


class CsvImport(BaseModel):
    # About 2 MB of text, far beyond any of these lists.
    csv: str = Field(max_length=2_000_000)
    dry_run: bool = True


class CheckpointOut(_Out):
    id: UUID
    key: str
    label_en: str
    label_ja: str | None
    offset_days: int
    remind_days_before: int
    field_versions: dict[str, int]


class MeasureOut(_Out):
    id: UUID
    key: str
    metric: str
    checkpoint_id: UUID | None
    source: str
    applicability: str
    unit: str
    label_en: str
    label_ja: str | None
    position: int
    is_active: bool
    collected_from: date | None
    field_versions: dict[str, int]


class MeasureCreate(BaseModel):
    metric: str
    checkpoint_id: UUID
    label_en: str
    label_ja: str | None = None


class CoreFieldOut(_Out):
    id: UUID
    key: str
    label_en: str | None
    label_ja: str | None
    hidden: bool
    required: bool
    position: int
    can_hide: bool
    can_require: bool
    field_versions: dict[str, int]


class Reorder(BaseModel):
    ids: list[UUID]


class CustomFieldOut(_Out):
    id: UUID
    key: str
    label_en: str
    label_ja: str | None
    help_en: str | None
    help_ja: str | None
    field_type: str
    options: list[dict[str, Any]]
    vocabulary_id: UUID | None
    scope: str
    owner_id: UUID | None
    owner_name: str | None = None
    owner_active: bool | None = None
    required: bool
    position: int
    is_active: bool
    due_checkpoint_id: UUID | None
    score_eligible: bool
    field_versions: dict[str, int]


class CustomFieldCreate(BaseModel):
    scope: str
    label_en: str
    label_ja: str | None = None
    help_en: str | None = None
    help_ja: str | None = None
    field_type: str
    options: list[dict[str, Any]] = []
    vocabulary_id: UUID | None = None
    due_checkpoint_id: UUID | None = None
    required: bool = False
    score_eligible: bool = False


class TransferOwner(BaseModel):
    owner_id: UUID


class ResearcherOut(_Out):
    id: UUID
    merged_into_id: UUID | None
    name: str
    given_name: str | None
    family_name: str | None
    name_ja: str | None
    current_unit_id: UUID | None
    gender: str
    researchmap_id: str | None
    orcid: str | None
    status: str
    notes: str | None
    created_at: datetime
    field_versions: dict[str, int]
    release_count: int = 0
    # Other records with the same name, which are different people until merged (R6.3.1).
    same_name_count: int = 0
    # Records merged into this one, whose merge can still be undone.
    merged_count: int = 0


class ResearcherPage(BaseModel):
    items: list[ResearcherOut]
    total: int


class ResearcherRelease(_Out):
    """Enough to recognise a release by."""

    id: UUID
    code: str | None
    title: str | None
    paper_title: str | None
    release_date: date | None


class MergedRecord(_Out):
    id: UUID
    name: str
    updated_at: datetime
    release_count: int = 0


class ResearcherDetail(ResearcherOut):
    releases: list[ResearcherRelease] = []
    merged_records: list[MergedRecord] = []


class ResearcherCreate(BaseModel):
    name: str
    given_name: str | None = None
    family_name: str | None = None
    name_ja: str | None = None
    current_unit_id: UUID | None = None
    gender: str = "not_recorded"
    status: str = "incomplete"


class MergeResearchers(BaseModel):
    into_id: UUID


class SplitResearcher(BaseModel):
    """Move these releases to another record: an existing one, or a new one."""

    release_ids: list[UUID] = Field(min_length=1)
    into_id: UUID | None = None
    name: str | None = None
    notes: str | None = None


class SplitResult(BaseModel):
    source: ResearcherOut
    target: ResearcherOut
    created: bool


class UnmergeResult(BaseModel):
    restored: ResearcherOut
    survivor: ResearcherOut
