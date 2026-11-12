"""Custom fields: institution fields for admins, personal fields for their owners (section 6.6).

Everyone can see every field, labelled with its owner (R6.6.2). Only the owner changes a
personal field, which an admin can transfer, and an admin or the owner can turn into an
institution field. Values are
kept by field key, so neither of those touches them (R3.4.3).
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user, require_admin, require_editor
from app.models import Checkpoint, CustomField, User, UserRole, Vocabulary
from app.schemas.settings import CustomFieldCreate, CustomFieldOut, Reorder, TransferOwner
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
    slugify,
)

router = APIRouter(prefix="/custom-fields", tags=["custom fields"])

FIELD_TYPES = (
    "integer",
    "number",
    "text",
    "long_text",
    "date",
    "boolean",
    "single_select",
    "multi_select",
    "url",
)
_NUMERIC = ("integer", "number")


def _parse_options(value: Any) -> list[dict[str, Any]]:
    """Options written on the field: each has an English label and a Japanese one."""
    if value is None:
        return []
    if not isinstance(value, list):
        raise field_error("field_invalid")
    options: dict[str, dict[str, Any]] = {}
    for item in value:
        if not isinstance(item, dict):
            raise field_error("field_invalid")
        label_en = str(item.get("label_en") or "").strip()
        if not label_en:
            raise field_error("field_required")
        label_ja = str(item.get("label_ja") or "").strip() or None
        key = str(item.get("key") or "") or slugify(label_en, "option")
        options[key] = {"key": key, "label_en": label_en, "label_ja": label_ja}
    return list(options.values())


SHARED_SPECS: dict[str, FieldSpec] = {
    "label_en": field_patch.text(required=True),
    "label_ja": field_patch.text(),
    "help_en": field_patch.text(2000),
    "help_ja": field_patch.text(2000),
    "options": FieldSpec(_parse_options),
    "vocabulary_id": field_patch.reference(Vocabulary),
    "due_checkpoint_id": field_patch.reference(Checkpoint),
    "is_active": field_patch.boolean(),
}
INSTITUTION_SPECS: dict[str, FieldSpec] = {
    **SHARED_SPECS,
    "required": field_patch.boolean(),
    "score_eligible": field_patch.boolean(),
}


def _out(field: CustomField, owner: User | None) -> dict[str, Any]:
    data = CustomFieldOut.model_validate(field)
    if owner is not None:
        data.owner_name = owner.full_name or owner.email
        data.owner_active = owner.is_active
    return data.model_dump(mode="json")


async def _unique_key(db: AsyncSession, institution_id: UUID, label: str) -> str:
    base = slugify(label, "field")
    taken = set(
        await db.scalars(
            select(CustomField.key).where(CustomField.institution_id == institution_id)
        )
    )
    if base not in taken:
        return base
    suffix = 2
    while f"{base}_{suffix}" in taken:
        suffix += 1
    return f"{base}_{suffix}"


async def _can_edit(db: AsyncSession, field: CustomField, user: User) -> None:
    if field.scope == "institution":
        if user.role != UserRole.admin:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="admin_required")
    elif field.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="personal_field_read_only")


@router.get("")
async def list_custom_fields(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[dict[str, Any]]:
    rows = await db.execute(
        select(CustomField, User)
        .outerjoin(User, User.id == CustomField.owner_id)
        .where(CustomField.institution_id == user.institution_id)
        .order_by(CustomField.scope, CustomField.position, CustomField.label_en)
    )
    return [_out(field, owner) for field, owner in rows.all()]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_custom_field(
    payload: CustomFieldCreate,
    user: User = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    institution_id = user.institution_id
    if payload.scope == "institution":
        if user.role != UserRole.admin:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="admin_required")
    elif payload.scope != "personal":
        raise field_error("field_invalid")
    if payload.field_type not in FIELD_TYPES:
        raise field_error("field_invalid")
    is_personal = payload.scope == "personal"
    if is_personal and (payload.required or payload.score_eligible):
        raise field_error("field_not_editable")
    if payload.score_eligible and payload.field_type not in _NUMERIC:
        raise field_error("score_eligible_numeric_only")

    values = {
        name: await clean_value(db, institution_id, SHARED_SPECS[name], getattr(payload, name))
        for name in (
            "label_en",
            "label_ja",
            "help_en",
            "help_ja",
            "options",
            "vocabulary_id",
            "due_checkpoint_id",
        )
    }
    position = await db.scalar(
        select(func.coalesce(func.max(CustomField.position), -1)).where(
            CustomField.institution_id == institution_id,
            CustomField.scope == payload.scope,
        )
    )
    field = CustomField(
        institution_id=institution_id,
        key=await _unique_key(db, institution_id, values["label_en"]),
        field_type=payload.field_type,
        scope=payload.scope,
        owner_id=user.id if is_personal else None,
        required=payload.required,
        score_eligible=payload.score_eligible,
        position=position + 1,
        **values,
    )
    db.add(field)
    await commit_unique(db)
    return _out(field, user if is_personal else None)


@router.post("/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_custom_fields(
    payload: Reorder,
    user: User = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
) -> None:
    rows = {
        field.id: field
        for field in await db.scalars(
            select(CustomField)
            .where(
                CustomField.id.in_(payload.ids),
                CustomField.institution_id == user.institution_id,
            )
            .with_for_update()
        )
    }
    if set(payload.ids) != set(rows):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
    for position, field_id in enumerate(payload.ids):
        await _can_edit(db, rows[field_id], user)
        rows[field_id].position = position
    await db.commit()


@router.patch("/{field_id}")
async def patch_custom_field(
    field_id: UUID,
    patch: FieldPatch,
    user: User = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Type and key stay fixed: stored values depend on them."""
    field = await load_for_update(db, CustomField, field_id, user.institution_id)
    await _can_edit(db, field, user)
    specs = INSTITUTION_SPECS if field.scope == "institution" else SHARED_SPECS
    if patch.field == "score_eligible" and patch.value and field.field_type not in _NUMERIC:
        raise field_error("score_eligible_numeric_only")
    version = await patch_field(db, field, specs, patch, user.institution_id)
    await commit_unique(db)
    return patch_result(patch.field, getattr(field, patch.field), version)


@router.post("/{field_id}/transfer")
async def transfer_custom_field(
    field_id: UUID,
    payload: TransferOwner,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    field = await load_for_update(db, CustomField, field_id, admin.institution_id)
    if field.scope != "personal":
        raise field_error("field_not_editable")
    owner = await db.get(User, payload.owner_id)
    if (
        owner is None
        or owner.institution_id != admin.institution_id
        or not owner.is_active
        or owner.role == UserRole.viewer
    ):
        raise field_error("owner_must_edit")
    field.owner_id = owner.id
    await commit_unique(db)
    return _out(field, owner)


@router.post("/{field_id}/convert")
async def convert_custom_field(
    field_id: UUID,
    user: User = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """A personal field becomes a shared one, for everyone to see and fill. An admin can do it
    (R6.6.2), and so can the field's owner (Daniel, 2026-11-12); admins look after it then."""
    field = await load_for_update(db, CustomField, field_id, user.institution_id)
    if field.scope != "personal":
        raise field_error("field_not_editable")
    if user.role != UserRole.admin and field.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="personal_field_read_only")
    field.scope = "institution"
    field.owner_id = None
    await commit_unique(db)
    return _out(field, None)
