"""The report export of the Data page (R7.6.2): one row per release, in English or Japanese.

Wide format: the release's fields, then one column per measure, then custom fields, with a
colleague's personal fields labelled with their name. A measure holds its number, "N/A" when
it does not apply, and nothing when it is missing or not yet due (R6.5.1). Headers and list
values follow the chosen language; free text stays as written (R5.4.5).

The full backup-style export is ``app/routers/data_export.py``.
"""

import csv
import io
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.i18n import t
from app.models import (
    CoreFieldConfig,
    CustomField,
    Institution,
    Measure,
    Reading,
    Release,
    Researcher,
    ResearchField,
    Unit,
    User,
    VocabularyItem,
    Writer,
)
from app.services.readings import STATE_NOT_APPLICABLE, STATE_VALUE
from app.services.release_codes import academic_year

# These come first, as in the grid: what a person looks a release up by.
_LEADING = ("code", "academic_year", "release_date", "title")
# Spreadsheets would run a cell starting with one of these as a formula.
_FORMULA_STARTS = ("=", "+", "-", "@", "\t", "\r")
_WIDTH_SAMPLE_ROWS = 200
_MIN_WIDTH, _MAX_WIDTH = 8, 60
_DATE_FORMAT = "yyyy-mm-dd"


@dataclass
class Table:
    headers: list[str]
    rows: list[list[Any]] = field(default_factory=list)


@dataclass
class Lookups:
    language: str
    units: dict[UUID, Unit]
    fields: dict[UUID, ResearchField]
    writers: dict[UUID, Writer]
    researchers: dict[UUID, Researcher]
    readings: dict[tuple[UUID, UUID], Reading]
    choices: dict[str, dict[str, str]]

    def named(self, en: str | None, ja: str | None) -> str | None:
        return (self.language == "ja" and ja) or en


def _yes_no(language: str, value: bool) -> str:
    return t(language, "export.values.yes" if value else "export.values.no")


def _number(value: Decimal | int | float | None) -> int | float | None:
    if value is None:
        return None
    number = Decimal(value)
    return int(number) if number == number.to_integral_value() else float(number)


def _as_date(value: Any) -> date | Any:
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return value
    return value


def _author_name(author: dict[str, Any]) -> str:
    return author.get("name") or " ".join(
        part for part in (author.get("given"), author.get("family")) if part
    )


def _core_value(key: str, release: Release, look: Lookups, start_month: int) -> Any:
    language = look.language
    if key == "academic_year":
        if release.release_date is None:
            return None
        year = academic_year(release.release_date, start_month)
        return t(language, "export.values.academic_year", year=year)
    if key == "writer":
        writer = look.writers.get(release.writer_id)
        return look.named(writer.display_name_en, writer.display_name_ja) if writer else None
    if key == "researcher":
        person = look.researchers.get(release.researcher_id)
        return look.named(person.name, person.name_ja) if person else None
    if key == "unit":
        unit = look.units.get(release.unit_id)
        return look.named(unit.name_en, unit.name_ja) if unit else None
    if key == "field":
        research_field = look.fields.get(release.field_id)
        return (
            look.named(research_field.name_en, research_field.name_ja) if research_field else None
        )
    if key in ("embargoed", "ea_top_page"):
        return _yes_no(language, bool(getattr(release, key)))
    if key == "release_time_et":
        return release.release_time_et.strftime("%H:%M") if release.release_time_et else None
    if key == "authors":
        return "; ".join(filter(None, map(_author_name, release.authors))) or None
    return getattr(release, key)


def _custom_value(custom: CustomField, release: Release, look: Lookups) -> Any:
    stored = release.custom_values.get(custom.key)
    if not stored:
        return None
    if stored.get("state") == STATE_NOT_APPLICABLE:
        return t(look.language, "export.values.not_applicable")
    value = stored.get("value")
    labels = look.choices.get(custom.key, {})
    if custom.field_type == "boolean":
        return _yes_no(look.language, bool(value))
    if custom.field_type == "single_select":
        return labels.get(value, value)
    if custom.field_type == "multi_select":
        return "; ".join(labels.get(item, str(item)) for item in value or [])
    if custom.field_type in ("integer", "number"):
        return _number(value)
    if custom.field_type == "date":
        return _as_date(value)
    return value


def _measure_value(measure: Measure, release: Release, look: Lookups) -> Any:
    reading = look.readings.get((release.id, measure.id))
    if reading is None or reading.state == STATE_NOT_APPLICABLE:
        # An inactive or absent reading cannot exist for this release.
        return t(look.language, "export.values.not_applicable")
    if reading.state == STATE_VALUE:
        return _number(reading.value)
    return None


async def _choices(
    db: AsyncSession, customs: list[CustomField], language: str
) -> dict[str, dict[str, str]]:
    def label(entry: dict[str, Any] | VocabularyItem) -> str:
        get = entry.get if isinstance(entry, dict) else lambda name: getattr(entry, name)
        return (language == "ja" and get("label_ja")) or get("label_en")

    vocabularies = {custom.vocabulary_id for custom in customs if custom.vocabulary_id}
    items: dict[UUID, list[VocabularyItem]] = {}
    if vocabularies:
        for item in await db.scalars(
            select(VocabularyItem).where(VocabularyItem.vocabulary_id.in_(vocabularies))
        ):
            items.setdefault(item.vocabulary_id, []).append(item)
    result: dict[str, dict[str, str]] = {}
    for custom in customs:
        entries = items.get(custom.vocabulary_id, []) if custom.vocabulary_id else custom.options
        result[custom.key] = {
            (entry["key"] if isinstance(entry, dict) else entry.key): label(entry)
            for entry in entries
        }
    return result


async def release_table(
    db: AsyncSession, institution: Institution, releases: list[Release], language: str
) -> Table:
    """The Releases sheet: headers in the chosen language, and one row per release."""
    configs = list(
        await db.scalars(
            select(CoreFieldConfig)
            .where(
                CoreFieldConfig.institution_id == institution.id,
                CoreFieldConfig.hidden.is_(False),
            )
            .order_by(CoreFieldConfig.position, CoreFieldConfig.key)
        )
    )
    labels = {
        config.key: (language == "ja" and config.label_ja) or config.label_en for config in configs
    }
    present = [config.key for config in configs]
    keys = [key for key in _LEADING if key in present or key == "academic_year"] + [
        key for key in present if key not in _LEADING
    ]
    measures = list(
        await db.scalars(
            select(Measure)
            .where(Measure.institution_id == institution.id, Measure.is_active.is_(True))
            .order_by(Measure.position, Measure.key)
        )
    )
    customs = list(
        await db.scalars(
            select(CustomField)
            .where(CustomField.institution_id == institution.id, CustomField.is_active.is_(True))
            .order_by(CustomField.position, CustomField.key)
        )
    )
    owners = {
        user.id: user.full_name or user.email
        for user in await db.scalars(
            select(User).where(User.id.in_({c.owner_id for c in customs if c.owner_id}))
        )
    }
    # The institution's fields first, then personal ones by owner, as on the Data page.
    customs.sort(key=lambda c: (c.scope != "institution", owners.get(c.owner_id, ""), c.position))

    release_ids = [release.id for release in releases]
    in_institution = Unit.institution_id == institution.id
    look = Lookups(
        language=language,
        units={unit.id: unit for unit in await db.scalars(select(Unit).where(in_institution))},
        fields={
            row.id: row
            for row in await db.scalars(
                select(ResearchField).where(ResearchField.institution_id == institution.id)
            )
        },
        writers={
            row.id: row
            for row in await db.scalars(
                select(Writer).where(Writer.institution_id == institution.id)
            )
        },
        researchers={
            row.id: row
            for row in await db.scalars(
                select(Researcher).where(
                    Researcher.id.in_({r.researcher_id for r in releases if r.researcher_id})
                )
            )
        },
        readings={
            (reading.release_id, reading.measure_id): reading
            for reading in await db.scalars(
                select(Reading).where(Reading.release_id.in_(release_ids))
            )
        }
        if release_ids
        else {},
        choices=await _choices(db, customs, language),
    )

    columns: list[tuple[str, Callable[[Release], Any]]] = []
    for key in keys:
        header = labels.get(key) or t(language, f"export.fields.{key}")
        columns.append(
            (
                header,
                lambda release, key=key: _core_value(
                    key, release, look, institution.ay_start_month
                ),
            )
        )
    for measure in measures:
        columns.append(
            (
                look.named(measure.label_en, measure.label_ja) or measure.key,
                lambda release, measure=measure: _measure_value(measure, release, look),
            )
        )
    for custom in customs:
        header = look.named(custom.label_en, custom.label_ja) or custom.key
        if custom.scope == "personal":
            header = t(
                language, "export.owned_by", label=header, owner=owners.get(custom.owner_id, "")
            )
        columns.append(
            (header, lambda release, custom=custom: _custom_value(custom, release, look))
        )

    table = Table(headers=[header for header, _ in columns])
    table.rows = [[value(release) for _, value in columns] for release in releases]
    return table


async def list_tables(
    db: AsyncSession, institution: Institution, language: str
) -> dict[str, Table]:
    """The Units and Fields sheets, so a report can be read without the app."""
    fields = list(
        await db.scalars(
            select(ResearchField)
            .where(ResearchField.institution_id == institution.id)
            .order_by(ResearchField.name_en)
        )
    )
    field_names = {row.id: (language == "ja" and row.name_ja) or row.name_en for row in fields}
    units = await db.scalars(
        select(Unit).where(Unit.institution_id == institution.id).order_by(Unit.name_en)
    )

    def heading(name: str) -> str:
        return t(language, f"export.list_columns.{name}")

    unit_table = Table(
        headers=[
            heading(name)
            for name in ("key", "name", "short_label", "type", "default_field", "active")
        ]
    )
    for unit in units:
        unit_table.rows.append(
            [
                unit.key,
                (language == "ja" and unit.name_ja) or unit.name_en,
                unit.short_label,
                t(language, f"export.unit_types.{unit.unit_type}") if unit.unit_type else None,
                field_names.get(unit.default_field_id),
                _yes_no(language, unit.is_active),
            ]
        )
    field_table = Table(headers=[heading(name) for name in ("name", "scope_note", "active")])
    for row in fields:
        field_table.rows.append(
            [field_names[row.id], row.scope_note, _yes_no(language, row.is_active)]
        )
    return {
        t(language, "export.sheets.units"): unit_table,
        t(language, "export.sheets.fields"): field_table,
    }


def read_me(language: str, *, when: datetime, who: str, count: int, scope: str | None) -> list[str]:
    """What the file is, and how to read it. ``scope`` describes the filters, if any."""
    lines = [
        t(language, "export.readme.title"),
        t(language, "export.readme.exported", when=when.strftime("%Y-%m-%d %H:%M"), who=who),
        t(
            language,
            "export.readme.scope_view" if scope is not None else "export.readme.scope_all",
            count=count,
        ),
    ]
    if scope:
        lines.append(t(language, "export.readme.filters", filters=scope))
    lines += [
        "",
        t(language, "export.readme.states_heading"),
        t(language, "export.readme.state_value"),
        t(language, "export.readme.state_na"),
        t(language, "export.readme.state_empty"),
        "",
        t(language, "export.readme.year"),
        t(language, "export.readme.colleagues"),
        "",
        t(language, "export.readme.personal"),
    ]
    return lines


def _display_width(value: Any) -> int:
    text = value.isoformat() if isinstance(value, date) else str(value)
    return sum(2 if unicodedata.east_asian_width(char) in "WF" else 1 for char in text)


def _write_sheet(sheet: Any, table: Table) -> None:
    bold = Font(bold=True)
    for column, header in enumerate(table.headers, start=1):
        cell = sheet.cell(row=1, column=column, value=header)
        cell.font = bold
        cell.data_type = "s"
    for row_number, row in enumerate(table.rows, start=2):
        for column, value in enumerate(row, start=1):
            cell = sheet.cell(row=row_number, column=column, value=value)
            if isinstance(value, str):
                # Text starting with "=" must stay text, never run as a formula.
                cell.data_type = "s"
            elif isinstance(value, date):
                cell.number_format = _DATE_FORMAT
    for column, header in enumerate(table.headers, start=1):
        sample = [row[column - 1] for row in table.rows[:_WIDTH_SAMPLE_ROWS]]
        widest = max(
            [_display_width(header)] + [_display_width(v) for v in sample if v is not None]
        )
        width = min(max(widest, _MIN_WIDTH), _MAX_WIDTH) + 2
        sheet.column_dimensions[get_column_letter(column)].width = width
    sheet.freeze_panes = "B2"
    if table.headers:
        sheet.auto_filter.ref = f"A1:{get_column_letter(len(table.headers))}{len(table.rows) + 1}"


def to_xlsx(
    releases_sheet: tuple[str, Table], lists: dict[str, Table], readme: tuple[str, list[str]]
) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = releases_sheet[0][:31]
    _write_sheet(sheet, releases_sheet[1])
    for name, table in lists.items():
        _write_sheet(workbook.create_sheet(name[:31]), table)
    notes = workbook.create_sheet(readme[0][:31])
    notes.column_dimensions["A"].width = 110
    for row, line in enumerate(readme[1], start=1):
        cell = notes.cell(row=row, column=1, value=line)
        cell.data_type = "s"
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        if row == 1:
            cell.font = Font(bold=True, size=14)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _csv_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        return f"'{value}" if value.startswith(_FORMULA_STARTS) else value
    return str(value)


def to_csv(table: Table) -> bytes:
    """UTF-8 with a byte-order mark, so Excel reads Japanese correctly (R7.6.2)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow([_csv_cell(header) for header in table.headers])
    writer.writerows([[_csv_cell(value) for value in row] for row in table.rows])
    return buffer.getvalue().encode("utf-8-sig")
