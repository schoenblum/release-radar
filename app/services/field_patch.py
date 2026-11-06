"""Saves one field of a record, with optimistic concurrency (R3.3.2, R3.3.3).

The client names the field, the new value and the version of that field it last saw.
If someone else has changed the field since, the save is refused with the current value,
so the person can choose which to keep. Different fields never conflict.

Errors carry a code that the frontend translates. Invalid input for one field never
affects any other, because each field is saved on its own.
"""

import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from fastapi import HTTPException, status
from pydantic import BaseModel, EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.audit import to_json

_EMAIL = TypeAdapter(EmailStr)


class FieldPatch(BaseModel):
    field: str
    value: Any = None
    version: int = 0


class FieldConflict(Exception):
    """Someone else changed this field. Turned into a 409 by a handler in ``app.main``."""

    def __init__(self, field: str, current_value: Any, current_version: int) -> None:
        super().__init__(field)
        self.field = field
        self.current_value = current_value
        self.current_version = current_version


def field_error(code: str) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=code)


Parser = Callable[[Any], Any]


@dataclass(frozen=True)
class FieldSpec:
    """How to clean a value for one field, and what it must refer to if anything."""

    parse: Parser
    reference: type | None = None


def text(max_length: int = 255, *, required: bool = False) -> FieldSpec:
    def parse(value: Any) -> str | None:
        if value is None or (isinstance(value, str) and not value.strip()):
            if required:
                raise field_error("field_required")
            return None
        if not isinstance(value, str):
            raise field_error("field_invalid")
        value = value.strip()
        if len(value) > max_length:
            raise field_error("field_too_long")
        return value

    return FieldSpec(parse)


def boolean() -> FieldSpec:
    def parse(value: Any) -> bool:
        if not isinstance(value, bool):
            raise field_error("field_invalid")
        return value

    return FieldSpec(parse)


def integer(minimum: int, maximum: int) -> FieldSpec:
    def parse(value: Any) -> int:
        if isinstance(value, str):
            try:
                value = int(value.strip())
            except ValueError as exc:
                raise field_error("field_invalid") from exc
        if not isinstance(value, int) or isinstance(value, bool):
            raise field_error("field_invalid")
        if not minimum <= value <= maximum:
            raise field_error("field_out_of_range")
        return value

    return FieldSpec(parse)


def choice(*options: str, required: bool = True) -> FieldSpec:
    def parse(value: Any) -> str | None:
        if value in (None, "") and not required:
            return None
        if value not in options:
            raise field_error("field_invalid")
        return value

    return FieldSpec(parse)


def string_list() -> FieldSpec:
    """A list of short strings. A comma-separated string works too, for simple inputs."""

    def parse(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = value.split(",")
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise field_error("field_invalid")
        cleaned = [item.strip() for item in value if item.strip()]
        if any(len(item) > 255 for item in cleaned):
            raise field_error("field_too_long")
        return list(dict.fromkeys(cleaned))

    return FieldSpec(parse)


def iso_date() -> FieldSpec:
    def parse(value: Any) -> date | None:
        if value in (None, ""):
            return None
        try:
            return date.fromisoformat(value)
        except (TypeError, ValueError) as exc:
            raise field_error("field_invalid") from exc

    return FieldSpec(parse)


def email() -> FieldSpec:
    def parse(value: Any) -> str | None:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        try:
            return _EMAIL.validate_python(value.strip() if isinstance(value, str) else value)
        except ValidationError as exc:
            raise field_error("invalid_email") from exc

    return FieldSpec(parse)


def reference(model: type) -> FieldSpec:
    def parse(value: Any) -> uuid.UUID | None:
        if value in (None, ""):
            return None
        try:
            return uuid.UUID(str(value))
        except ValueError as exc:
            raise field_error("field_invalid") from exc

    return FieldSpec(parse, reference=model)


def slugify(label: str, fallback: str = "item") -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")[:48] or fallback


async def clean_value(
    db: AsyncSession, institution_id: uuid.UUID, spec: FieldSpec, raw: Any
) -> Any:
    value = spec.parse(raw)
    if spec.reference is not None and value is not None:
        row = await db.get(spec.reference, value)
        if row is None or row.institution_id != institution_id:
            raise field_error("unknown_reference")
    return value


def set_versioned(record: Any, field: str, value: Any) -> int:
    """Set a field and raise its version. Returns the new version."""
    version = record.field_versions.get(field, 0) + 1
    setattr(record, field, value)
    record.field_versions = {**record.field_versions, field: version}
    return version


async def patch_field(
    db: AsyncSession,
    record: Any,
    specs: dict[str, FieldSpec],
    patch: FieldPatch,
    institution_id: uuid.UUID,
) -> int:
    """Apply one field to a record locked by ``load_for_update``. Returns its new version."""
    spec = specs.get(patch.field)
    if spec is None:
        raise field_error("field_not_editable")
    current_version = record.field_versions.get(patch.field, 0)
    if patch.version != current_version:
        raise FieldConflict(patch.field, getattr(record, patch.field), current_version)
    value = await clean_value(db, institution_id, spec, patch.value)
    if value == getattr(record, patch.field):
        return current_version
    return set_versioned(record, patch.field, value)


async def load_for_update(
    db: AsyncSession, model: type, record_id: uuid.UUID, institution_id: uuid.UUID
) -> Any:
    """Load a record and hold its row until commit, so two saves cannot interleave."""
    record = await db.scalar(
        select(model)
        .where(model.id == record_id, model.institution_id == institution_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
    return record


async def commit_unique(db: AsyncSession) -> None:
    """Commit, explaining a clash with a unique value in plain terms."""
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail="value_in_use") from exc


def patch_result(field: str, value: Any, version: int) -> dict[str, Any]:
    return {"field": field, "value": to_json(value), "version": version}
