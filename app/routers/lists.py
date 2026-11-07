"""List editors: units, fields, writers and vocabularies (R5.4.3, step 1.3).

Everyone signed in can read the lists, because the grid needs them. Only admins change
them. Entries are retired by switching off "active", never deleted, as releases may
refer to them.

CSV uses plain column names and both languages side by side, so a file can go straight
back in. Importing updates entries by their key. A column the file leaves out is left
alone, so a file with just two columns changes just those. A cell that cannot be used is
reported by row and column, and costs only that cell: the rest of its row still applies. A
dry run does the real work and rolls it back, so the preview cannot disagree with the result.
"""

import csv
import io
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user, require_admin
from app.models import ResearchField, Unit, User, Vocabulary, VocabularyItem, Writer
from app.schemas.settings import (
    CreateEntry,
    CsvImport,
    ResearchFieldOut,
    UnitOut,
    VocabularyItemOut,
    VocabularyOut,
    WriterOut,
)
from app.services import field_patch
from app.services.field_patch import (
    FieldPatch,
    FieldSpec,
    clean_value,
    commit_unique,
    field_error,
    load_for_update,
    patch_field,
    patch_result,
    set_versioned,
    slugify,
)

router = APIRouter(prefix="/lists", tags=["lists"])

_TRUE = {"y", "yes", "true", "1", "on", "active", "はい", "有効"}
_FALSE = {"n", "no", "false", "0", "off", "inactive", "いいえ", "無効"}
_UNIT_TYPES = ("school", "institute", "center", "other")
# What people type after seeing the Lists page, in either language.
_UNIT_TYPE_SPELLINGS = {
    **{name: name for name in _UNIT_TYPES},
    "centre": "center",
    "研究科・学部": "school",
    "研究科": "school",
    "学部": "school",
    "研究所": "institute",
    "センター": "center",
    "その他": "other",
}
# Spreadsheets would run a cell starting with one of these as a formula.
_FORMULA_STARTS = ("=", "+", "-", "@")


def _csv_safe(value: str) -> str:
    return f"'{value}" if value.startswith(_FORMULA_STARTS) else value


def _from_csv(value: str | None) -> str:
    value = (value or "").strip()
    if value.startswith("'") and value[1:].startswith(_FORMULA_STARTS):
        return value[1:]
    return value


def _flag(value: bool) -> str:
    return "Y" if value else "N"


# ---------------------------------------------------------------- CSV: what each list holds


@dataclass(frozen=True)
class CsvContext:
    fields_by_id: dict[UUID, str]
    fields_by_name: dict[str, UUID]
    users_by_id: dict[UUID, str]
    users_by_email: dict[str, UUID]


async def _csv_context(db: AsyncSession, institution_id: UUID) -> CsvContext:
    fields = list(
        await db.scalars(
            select(ResearchField).where(ResearchField.institution_id == institution_id)
        )
    )
    users = list(await db.scalars(select(User).where(User.institution_id == institution_id)))
    return CsvContext(
        fields_by_id={field.id: field.name_en for field in fields},
        fields_by_name={field.name_en.lower(): field.id for field in fields},
        users_by_id={user.id: user.email for user in users},
        users_by_email={user.email: user.id for user in users},
    )


def _as_written(cell: str, _context: CsvContext, _current: Any) -> Any:
    return cell


def _read_flag(cell: str, _context: CsvContext, current: Any) -> bool:
    """An empty cell keeps the current state, and a new entry starts active."""
    lowered = cell.lower()
    if lowered in _TRUE:
        return True
    if lowered in _FALSE:
        return False
    if lowered == "":
        return current.is_active if current is not None else True
    raise field_error("field_invalid")


def _read_unit_type(cell: str, _context: CsvContext, _current: Any) -> str | None:
    # An unknown word goes through, for the field's own check to refuse.
    return _UNIT_TYPE_SPELLINGS.get(cell.lower(), cell)


def _read_field_name(cell: str, context: CsvContext, _current: Any) -> UUID | None:
    if not cell:
        return None
    if cell.lower() not in context.fields_by_name:
        raise field_error("unknown_reference")
    return context.fields_by_name[cell.lower()]


def _read_user_email(cell: str, context: CsvContext, _current: Any) -> UUID | None:
    if not cell:
        return None
    if cell.lower() not in context.users_by_email:
        raise field_error("unknown_reference")
    return context.users_by_email[cell.lower()]


def _no_suggestions(_context: CsvContext) -> list[str]:
    return []


def _field_names(context: CsvContext) -> list[str]:
    return sorted(context.fields_by_id.values())


@dataclass(frozen=True)
class CsvColumn:
    """One column of a list's file."""

    name: str
    attribute: str
    read: Callable[[str, CsvContext, Any], Any] = _as_written
    # What to use instead, shown when a cell is refused.
    allowed: Callable[[CsvContext], list[str]] = _no_suggestions
    # An empty name takes the row's key, so a new entry needs only that.
    falls_back_to_key: bool = False


_ACTIVE_COLUMN = CsvColumn("active", "is_active", _read_flag, lambda _: ["Y", "N"])


def _unit_row(unit: Unit, context: CsvContext) -> dict[str, str]:
    return {
        "key": unit.key,
        "name_en": unit.name_en,
        "name_ja": unit.name_ja or "",
        "short_label": unit.short_label or "",
        "type": unit.unit_type or "",
        "aliases": ", ".join(unit.aliases),
        "default_field": context.fields_by_id.get(unit.default_field_id, ""),
        "active": _flag(unit.is_active),
    }


def _field_row(field: ResearchField, _: CsvContext) -> dict[str, str]:
    return {
        "name_en": field.name_en,
        "name_ja": field.name_ja or "",
        "scope_note": field.scope_note or "",
        "active": _flag(field.is_active),
    }


def _writer_row(writer: Writer, context: CsvContext) -> dict[str, str]:
    return {
        "display_name_en": writer.display_name_en,
        "display_name_ja": writer.display_name_ja or "",
        "full_name": writer.full_name or "",
        "user_email": context.users_by_id.get(writer.user_id, ""),
        "active": _flag(writer.is_active),
    }


def _item_row(item: VocabularyItem, _: CsvContext) -> dict[str, str]:
    return {
        "key": item.key,
        "label_en": item.label_en,
        "label_ja": item.label_ja or "",
        "aliases": ", ".join(item.aliases),
        "active": _flag(item.is_active),
    }


@dataclass(frozen=True)
class ListConfig:
    model: type
    out: type[BaseModel]
    specs: dict[str, FieldSpec]
    required: tuple[str, ...]
    order: str
    key_column: str = ""
    key_attribute: str = ""
    csv_columns: tuple[str | CsvColumn, ...] = ()
    to_row: Callable[[Any, CsvContext], dict[str, str]] | None = None

    @property
    def columns(self) -> tuple[str, ...]:
        """What the exported file holds, including a key that cannot be changed by import."""
        return tuple(c if isinstance(c, str) else c.name for c in self.csv_columns)

    @property
    def importable(self) -> tuple[CsvColumn, ...]:
        return tuple(c for c in self.csv_columns if isinstance(c, CsvColumn))


UNITS = ListConfig(
    model=Unit,
    out=UnitOut,
    specs={
        "name_en": field_patch.text(required=True),
        "name_ja": field_patch.text(),
        "short_label": field_patch.text(64),
        "unit_type": field_patch.choice(*_UNIT_TYPES, required=False),
        "aliases": field_patch.string_list(),
        "default_field_id": field_patch.reference(ResearchField),
        "is_active": field_patch.boolean(),
    },
    required=("name_en",),
    order="name_en",
    key_column="key",
    key_attribute="key",
    csv_columns=(
        "key",
        CsvColumn("name_en", "name_en", falls_back_to_key=True),
        CsvColumn("name_ja", "name_ja"),
        CsvColumn("short_label", "short_label"),
        CsvColumn("type", "unit_type", _read_unit_type, lambda _: list(_UNIT_TYPES)),
        CsvColumn("aliases", "aliases"),
        CsvColumn("default_field", "default_field_id", _read_field_name, _field_names),
        _ACTIVE_COLUMN,
    ),
    to_row=_unit_row,
)
FIELDS = ListConfig(
    model=ResearchField,
    out=ResearchFieldOut,
    specs={
        "name_en": field_patch.text(required=True),
        "name_ja": field_patch.text(),
        "scope_note": field_patch.text(5000),
        "is_active": field_patch.boolean(),
    },
    required=("name_en",),
    order="name_en",
    key_column="name_en",
    key_attribute="name_en",
    csv_columns=(
        CsvColumn("name_en", "name_en", falls_back_to_key=True),
        CsvColumn("name_ja", "name_ja"),
        CsvColumn("scope_note", "scope_note"),
        _ACTIVE_COLUMN,
    ),
    to_row=_field_row,
)
WRITERS = ListConfig(
    model=Writer,
    out=WriterOut,
    specs={
        "display_name_en": field_patch.text(required=True),
        "display_name_ja": field_patch.text(),
        "full_name": field_patch.text(),
        "user_id": field_patch.reference(User),
        "is_active": field_patch.boolean(),
    },
    required=("display_name_en",),
    order="display_name_en",
    key_column="display_name_en",
    key_attribute="display_name_en",
    csv_columns=(
        CsvColumn("display_name_en", "display_name_en", falls_back_to_key=True),
        CsvColumn("display_name_ja", "display_name_ja"),
        CsvColumn("full_name", "full_name"),
        CsvColumn("user_email", "user_id", _read_user_email),
        _ACTIVE_COLUMN,
    ),
    to_row=_writer_row,
)
VOCABULARIES = ListConfig(
    model=Vocabulary,
    out=VocabularyOut,
    specs={
        "name_en": field_patch.text(required=True),
        "name_ja": field_patch.text(),
        "is_active": field_patch.boolean(),
    },
    required=("name_en",),
    order="name_en",
)
VOCABULARY_ITEMS = ListConfig(
    model=VocabularyItem,
    out=VocabularyItemOut,
    specs={
        "label_en": field_patch.text(required=True),
        "label_ja": field_patch.text(),
        "aliases": field_patch.string_list(),
        "position": field_patch.integer(0, 100_000),
        "is_active": field_patch.boolean(),
    },
    required=("label_en",),
    order="position",
    key_column="key",
    key_attribute="key",
    csv_columns=(
        "key",
        CsvColumn("label_en", "label_en", falls_back_to_key=True),
        CsvColumn("label_ja", "label_ja"),
        CsvColumn("aliases", "aliases"),
        _ACTIVE_COLUMN,
    ),
    to_row=_item_row,
)
CONFIGS = {"units": UNITS, "fields": FIELDS, "writers": WRITERS, "vocabularies": VOCABULARIES}


def _config(kind: str) -> ListConfig:
    config = CONFIGS.get(kind)
    if config is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
    return config


def _serialize(config: ListConfig, row: Any) -> dict[str, Any]:
    return config.out.model_validate(row).model_dump(mode="json")


async def _clean_new_values(
    db: AsyncSession, config: ListConfig, institution_id: UUID, values: dict[str, Any]
) -> dict[str, Any]:
    cleaned = {
        field: await clean_value(db, institution_id, config.specs[field], values.get(field))
        for field in config.specs
        if field in values or field in config.required
    }
    return cleaned


async def _unique_key(
    db: AsyncSession, model: type, label: str, *conditions: Any, attribute: str = "key"
) -> str:
    """A readable key from a label, with a number added if it is taken."""
    base = slugify(label)
    column = getattr(model, attribute)
    taken = set(await db.scalars(select(column).where(*conditions)))
    if base not in taken:
        return base
    suffix = 2
    while f"{base}_{suffix}" in taken:
        suffix += 1
    return f"{base}_{suffix}"


# ---------------------------------------------------------------- CSV: export and import


def _to_csv(config: ListConfig, rows: list[Any], context: CsvContext, filename: str) -> Response:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=config.columns, lineterminator="\r\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {key: _csv_safe(value) for key, value in config.to_row(row, context).items()}
        )
    # The byte-order mark makes Excel read the file as UTF-8, which Japanese needs.
    return Response(
        content="\ufeff" + buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _problem(
    row: int,
    key: str,
    column: str | None,
    value: str,
    code: str,
    allowed: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "row": row,
        "key": key,
        "column": column,
        "value": value[:80],
        "code": code,
        "allowed": allowed or [],
    }


async def _import_csv(
    db: AsyncSession,
    config: ListConfig,
    payload: CsvImport,
    institution_id: UUID,
    existing: list[Any],
    create: Callable[[str, dict[str, Any]], Awaitable[Any]],
) -> dict[str, Any]:
    reader = csv.DictReader(io.StringIO(payload.csv.lstrip("\ufeff")))
    if config.key_column not in (reader.fieldnames or []):
        raise field_error("csv_missing_column")
    context = await _csv_context(db, institution_id)
    by_key = {getattr(row, config.key_attribute).lower(): row for row in existing}
    report: dict[str, Any] = {"created": 0, "updated": 0, "unchanged": 0, "errors": []}

    for line, raw in enumerate(reader, start=2):
        row = {name: _from_csv(value) for name, value in raw.items() if name}
        key = row.get(config.key_column, "")
        if not key:
            report["errors"].append(_problem(line, key, config.key_column, "", "field_required"))
            continue
        current = by_key.get(key.lower())
        cleaned: dict[str, Any] = {}
        for column in config.importable:
            # Left out of the file means left alone.
            if column.name not in row and not (current is None and column.falls_back_to_key):
                continue
            cell = row.get(column.name, "")
            if not cell and column.falls_back_to_key:
                cell = key
            try:
                value = column.read(cell, context, current)
                spec = config.specs[column.attribute]
                cleaned[column.attribute] = await clean_value(db, institution_id, spec, value)
            except HTTPException as error:
                report["errors"].append(
                    _problem(line, key, column.name, cell, error.detail, column.allowed(context))
                )
        if current is None and any(field not in cleaned for field in config.required):
            continue
        # Each row in its own savepoint: a clash, such as two writers linked to one user,
        # costs that row and not the file.
        try:
            async with db.begin_nested():
                if current is None:
                    created = await create(key, cleaned)
                    changed = []
                else:
                    created = None
                    changed = [
                        field
                        for field, value in cleaned.items()
                        if getattr(current, field) != value
                    ]
                    for field in changed:
                        set_versioned(current, field, cleaned[field])
                await db.flush()
        except IntegrityError:
            if current is not None:
                await db.refresh(current)
            report["errors"].append(_problem(line, key, None, "", "value_in_use"))
            continue
        if created is not None:
            by_key[key.lower()] = created
            report["created"] += 1
        else:
            report["updated" if changed else "unchanged"] += 1

    if payload.dry_run:
        await db.rollback()
    else:
        await commit_unique(db)
    report["dry_run"] = payload.dry_run
    return report


# ---------------------------------------------------------------- vocabulary items
# Declared first: their paths are more specific than the general ones below.


async def _vocabulary(db: AsyncSession, vocabulary_id: UUID, institution_id: UUID) -> Vocabulary:
    vocabulary = await db.get(Vocabulary, vocabulary_id)
    if vocabulary is None or vocabulary.institution_id != institution_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
    return vocabulary


async def _items(db: AsyncSession, vocabulary_id: UUID) -> list[VocabularyItem]:
    return list(
        await db.scalars(
            select(VocabularyItem)
            .where(VocabularyItem.vocabulary_id == vocabulary_id)
            .order_by(VocabularyItem.position, VocabularyItem.label_en)
        )
    )


async def _new_item(
    db: AsyncSession, vocabulary: Vocabulary, key: str, values: dict[str, Any]
) -> VocabularyItem:
    position = await db.scalar(
        select(func.coalesce(func.max(VocabularyItem.position), -1)).where(
            VocabularyItem.vocabulary_id == vocabulary.id
        )
    )
    item = VocabularyItem(
        institution_id=vocabulary.institution_id,
        vocabulary_id=vocabulary.id,
        key=key,
        position=values.pop("position", position + 1),
        **values,
    )
    db.add(item)
    return item


@router.get("/vocabularies/{vocabulary_id}/items", response_model=list[VocabularyItemOut])
async def list_items(
    vocabulary_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[VocabularyItem]:
    await _vocabulary(db, vocabulary_id, user.institution_id)
    return await _items(db, vocabulary_id)


@router.post(
    "/vocabularies/{vocabulary_id}/items",
    response_model=VocabularyItemOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_item(
    vocabulary_id: UUID,
    payload: CreateEntry,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> VocabularyItem:
    vocabulary = await _vocabulary(db, vocabulary_id, admin.institution_id)
    values = await _clean_new_values(db, VOCABULARY_ITEMS, admin.institution_id, payload.values)
    key = await _unique_key(
        db,
        VocabularyItem,
        values["label_en"],
        VocabularyItem.vocabulary_id == vocabulary_id,
    )
    item = await _new_item(db, vocabulary, key, values)
    await commit_unique(db)
    return item


@router.get("/vocabularies/{vocabulary_id}/items/export")
async def export_items(
    vocabulary_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    vocabulary = await _vocabulary(db, vocabulary_id, admin.institution_id)
    context = await _csv_context(db, admin.institution_id)
    rows = await _items(db, vocabulary_id)
    return _to_csv(VOCABULARY_ITEMS, rows, context, f"vocabulary_{vocabulary.key}.csv")


@router.post("/vocabularies/{vocabulary_id}/items/import")
async def import_items(
    vocabulary_id: UUID,
    payload: CsvImport,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    vocabulary = await _vocabulary(db, vocabulary_id, admin.institution_id)

    async def create(key: str, values: dict[str, Any]) -> VocabularyItem:
        return await _new_item(db, vocabulary, key, values)

    return await _import_csv(
        db,
        VOCABULARY_ITEMS,
        payload,
        admin.institution_id,
        await _items(db, vocabulary_id),
        create,
    )


@router.patch("/vocabulary-items/{item_id}")
async def patch_item(
    item_id: UUID,
    patch: FieldPatch,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    item = await load_for_update(db, VocabularyItem, item_id, admin.institution_id)
    version = await patch_field(db, item, VOCABULARY_ITEMS.specs, patch, admin.institution_id)
    await commit_unique(db)
    return patch_result(patch.field, getattr(item, patch.field), version)


# ---------------------------------------------------------------- the lists themselves


async def _rows(db: AsyncSession, config: ListConfig, institution_id: UUID) -> list[Any]:
    model = config.model
    return list(
        await db.scalars(
            select(model)
            .where(model.institution_id == institution_id)
            .order_by(getattr(model, config.order))
        )
    )


async def _new_entry(
    db: AsyncSession, config: ListConfig, institution_id: UUID, key: str, values: dict[str, Any]
) -> Any:
    # Only these two keep a key apart from their name.
    extra = {"key": key} if config.model in (Unit, Vocabulary) else {}
    row = config.model(institution_id=institution_id, **extra, **values)
    db.add(row)
    return row


@router.get("/{kind}")
async def list_entries(
    kind: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    config = _config(kind)
    return [_serialize(config, row) for row in await _rows(db, config, user.institution_id)]


@router.post("/{kind}", status_code=status.HTTP_201_CREATED)
async def create_entry(
    kind: str,
    payload: CreateEntry,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    config = _config(kind)
    institution_id = admin.institution_id
    values = await _clean_new_values(db, config, institution_id, payload.values)
    key = ""
    if config.model is Unit:
        # What the workbook calls a unit. New units simply use their name.
        key = values["name_en"]
    elif config.model is Vocabulary:
        key = await _unique_key(
            db, Vocabulary, values["name_en"], Vocabulary.institution_id == institution_id
        )
    row = await _new_entry(db, config, institution_id, key, values)
    await commit_unique(db)
    return _serialize(config, row)


@router.get("/{kind}/export")
async def export_entries(
    kind: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    config = _config(kind)
    if config.to_row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
    context = await _csv_context(db, admin.institution_id)
    rows = await _rows(db, config, admin.institution_id)
    return _to_csv(config, rows, context, f"{kind}.csv")


@router.post("/{kind}/import")
async def import_entries(
    kind: str,
    payload: CsvImport,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    config = _config(kind)
    if not config.importable:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
    institution_id = admin.institution_id

    async def create(key: str, values: dict[str, Any]) -> Any:
        return await _new_entry(db, config, institution_id, key, values)

    return await _import_csv(
        db, config, payload, institution_id, await _rows(db, config, institution_id), create
    )


@router.patch("/{kind}/{record_id}")
async def patch_entry(
    kind: str,
    record_id: UUID,
    patch: FieldPatch,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    config = _config(kind)
    row = await load_for_update(db, config.model, record_id, admin.institution_id)
    version = await patch_field(db, row, config.specs, patch, admin.institution_id)
    await commit_unique(db)
    return patch_result(patch.field, getattr(row, patch.field), version)
