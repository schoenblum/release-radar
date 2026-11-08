"""Writes every change to an ``Audited`` record to the audit log (R3.4.4).

It hooks into the save itself, so no code path can forget it. Entries go in through the
same transaction as the change, so a rollback removes both. Changes made with bulk SQL
statements bypass this, so record changes must go through the ORM.

The actor comes from the session: ``set_actor`` is called once a request is
authenticated. With no actor set, the change is recorded as the system's.
"""

import enum
import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.institution import Institution
from app.models.mixins import ActorTracked, Audited

_ACTOR_KEY = "audit_actor_id"
_NOTE_KEY = "audit_note"
REDACTED = "[redacted]"
# Technical columns, on every model.
_ALWAYS_EXCLUDED = frozenset(
    {
        "id",
        "institution_id",
        "created_at",
        "updated_at",
        "created_by_id",
        "updated_by_id",
        "field_versions",
    }
)


def set_actor(db: AsyncSession, user_id: uuid.UUID | None) -> None:
    """Attribute the changes saved through this session to this user."""
    db.info[_ACTOR_KEY] = user_id


def set_note(db: AsyncSession, note: str | None) -> None:
    """Say how the changes saved through this session came about, such as an import."""
    db.info[_NOTE_KEY] = note


def to_json(value: Any) -> Any:
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime | date | time):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {key: to_json(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [to_json(item) for item in value]
    return value


def _audited_keys(obj: Audited) -> list[str]:
    excluded = _ALWAYS_EXCLUDED | obj.__audit_exclude__
    return [
        attribute.key
        for attribute in inspect(type(obj)).column_attrs
        if attribute.key not in excluded
    ]


def _changes(obj: Audited) -> list[tuple[str, Any, Any]]:
    """The net changes as (field, old, new), with redaction and per-key expansion applied."""
    state = inspect(obj)
    changes: list[tuple[str, Any, Any]] = []
    for key in _audited_keys(obj):
        history = state.attrs[key].history
        if not history.has_changes():
            continue
        old = history.deleted[0] if history.deleted else None
        new = history.added[0] if history.added else None
        if key in obj.__audit_redact__:
            changes.append((key, REDACTED, REDACTED))
        elif key in obj.__audit_expand__:
            old_map, new_map = old or {}, new or {}
            for item in sorted(old_map.keys() | new_map.keys()):
                if old_map.get(item) != new_map.get(item):
                    changes.append(
                        (f"{key}.{item}", to_json(old_map.get(item)), to_json(new_map.get(item)))
                    )
        else:
            changes.append((key, to_json(old), to_json(new)))
    return changes


def _snapshot(obj: Audited) -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    for key in _audited_keys(obj):
        value = getattr(obj, key)
        if value is None:
            continue
        snapshot[key] = REDACTED if key in obj.__audit_redact__ else to_json(value)
    return snapshot


def stamp_actors(session: Session) -> None:
    """Fill in who created and last changed a record. Only for real changes."""
    actor = session.info.get(_ACTOR_KEY)
    if actor is None:
        return
    for obj in session.new:
        if isinstance(obj, ActorTracked):
            obj.created_by_id = obj.created_by_id or actor
            obj.updated_by_id = actor
    for obj in session.dirty:
        if isinstance(obj, ActorTracked) and isinstance(obj, Audited) and _changes(obj):
            obj.updated_by_id = actor


def write_entries(session: Session) -> None:
    actor = session.info.get(_ACTOR_KEY)
    note = session.info.get(_NOTE_KEY)
    rows: list[dict[str, Any]] = []

    def add(obj: Audited, action: str, field: str | None, old: Any, new: Any) -> None:
        rows.append(
            {
                "id": uuid.uuid4(),
                "institution_id": obj.id if isinstance(obj, Institution) else obj.institution_id,
                "entity_type": obj.__tablename__,
                "entity_id": obj.id,
                "action": action,
                "field": field,
                "old_value": old,
                "new_value": new,
                "user_id": actor,
                "note": note,
            }
        )

    for obj in session.new:
        if isinstance(obj, Audited):
            add(obj, "create", None, None, _snapshot(obj))
    for obj in session.dirty:
        if isinstance(obj, Audited):
            for field, old, new in _changes(obj):
                add(obj, "update", field, old, new)
    for obj in session.deleted:
        if isinstance(obj, Audited):
            add(obj, "delete", None, _snapshot(obj), None)

    if rows:
        # Core, not the ORM: adding objects during a flush would need another flush.
        session.connection().execute(AuditLog.__table__.insert(), rows)
