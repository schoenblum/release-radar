"""Values of custom fields on a release (BRIEF section 6.6).

Stored on ``Release.custom_values`` by field key: ``{"state": "value", "value": ...}``, an
explicit N/A is ``{"state": "not_applicable"}``, and a key that is absent is missing. A wrapper,
so no real value can be mistaken for N/A.
"""

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CustomField, VocabularyItem
from app.services import field_patch
from app.services.field_patch import field_error, parse_number

STATE_VALUE = "value"
STATE_NOT_APPLICABLE = "not_applicable"
_TEXT_LIMITS = {"text": 2000, "long_text": 20000}


def _json_number(number: Decimal) -> int | float:
    return int(number) if number == number.to_integral_value() else float(number)


async def _allowed_keys(db: AsyncSession, field: CustomField) -> set[str]:
    if field.vocabulary_id is None:
        return {option["key"] for option in field.options}
    keys = await db.scalars(
        select(VocabularyItem.key).where(
            VocabularyItem.vocabulary_id == field.vocabulary_id,
            VocabularyItem.is_active.is_(True),
        )
    )
    return set(keys)


async def parse_value(db: AsyncSession, field: CustomField, raw: Any) -> Any:
    """What to store for this field, or None if the input is empty. Refuses what does not fit."""
    if raw is None or raw == [] or (isinstance(raw, str) and not raw.strip()):
        return None
    kind = field.field_type
    if kind == "integer":
        number = parse_number(raw)
        if number != number.to_integral_value():
            raise field_error("whole_number_required")
        return int(number)
    if kind == "number":
        return _json_number(parse_number(raw))
    if kind in _TEXT_LIMITS:
        return field_patch.text(_TEXT_LIMITS[kind]).parse(raw)
    if kind == "date":
        return field_patch.iso_date().parse(raw).isoformat()
    if kind == "boolean":
        return field_patch.boolean().parse(raw)
    if kind == "url":
        return field_patch.web_address().parse(raw)
    allowed = await _allowed_keys(db, field)
    if kind == "single_select":
        if raw not in allowed:
            raise field_error("field_invalid")
        return raw
    if kind == "multi_select":
        if not isinstance(raw, list) or not set(raw) <= allowed:
            raise field_error("field_invalid")
        return list(dict.fromkeys(raw))
    raise field_error("field_invalid")
