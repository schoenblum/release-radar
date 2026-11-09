"""Finds the columns of the old workbook and the intake workbook by their headings.

Columns are looked up by heading, and by the group heading above them where two share a name
(the release's Title and the paper's Title), so a column moved in the file still lands right.
"""

import io
import re
from dataclasses import dataclass, field
from typing import Any

from openpyxl import load_workbook

from app.services.workbook_import.values import text_of


class WorkbookProblem(Exception):
    """The file cannot be read as the workbook it should be. ``code`` names the problem."""

    def __init__(self, code: str, **details: Any) -> None:
        super().__init__(code)
        self.code = code
        self.details = details


RELEASE_SHEET = "PR DATA"
# Headings in row 2, grouped under row 1; data from row 3 (BRIEF step 1.8).
_HEADING_ROW, _GROUP_ROW, _FIRST_DATA_ROW = 2, 1, 3

# Our name: (heading, group heading or None when the heading alone is enough).
RELEASE_COLUMNS: dict[str, tuple[str, str | None]] = {
    "code": ("ID", None),
    "title": ("Title", "Press release"),
    "writer": ("Writer", None),
    "unit": ("School", None),
    "researcher": ("Researcher", None),
    "request_received": ("Request received", None),
    "gender": ("First author (M/F)", None),
    "embargo": ("Embargo", None),
    "paper_title": ("Title", "Paper"),
    "doi": ("DOI", None),
    "ea_views_d0": ("Embargoed views", None),
    "release_date": ("Release posted", None),
    "release_time": ("Time (ET)", None),
    "ea_views_d28": ("28 day", "EurekAlert"),
    "altmetric_d0": ("0 day", "Altmetrics"),
    "altmetric_d28": ("28 day score", None),
    "ea_url": ("EurekAlert", "URLs"),
    "website_url": ("Website", None),
    "bitly": ("28 day engagements", None),
    "pitches": ("Pitches", None),
    "notes": ("NOTES", None),
}
# Not imported on purpose (BRIEF step 1.8): the original workbook stays the archive.
SKIPPED_HEADINGS = ("1 day", "7 day", "1 day score", "7 day score")


def _key(text: Any) -> str:
    return text_of(text).casefold()


def open_workbook(content: bytes, label: str) -> Any:
    try:
        return load_workbook(io.BytesIO(content), data_only=True, read_only=False)
    except Exception as exc:  # openpyxl raises many kinds for a file that is not a workbook
        raise WorkbookProblem("not_a_workbook", file=label) from exc


@dataclass
class SourceRow:
    number: int
    cells: dict[str, Any]
    # As the workbook heads it, for the report.
    headings: dict[str, str]


def release_rows(content: bytes) -> list[SourceRow]:
    workbook = open_workbook(content, "release_list")
    if RELEASE_SHEET not in workbook.sheetnames:
        raise WorkbookProblem("sheet_missing", sheet=RELEASE_SHEET)
    sheet = workbook[RELEASE_SHEET]
    width = sheet.max_column
    groups: list[str] = []
    group = ""
    columns: list[tuple[str, str]] = []
    for index in range(1, width + 1):
        above = text_of(sheet.cell(_GROUP_ROW, index).value)
        heading = text_of(sheet.cell(_HEADING_ROW, index).value)
        if above:
            group = above
        groups.append(group)
        # A column headed only in the top row (Pitches, NOTES) is its own group.
        columns.append((heading or above, group))

    found: dict[str, int] = {}
    for name, (heading, wanted_group) in RELEASE_COLUMNS.items():
        matches = [
            index
            for index, (text, group) in enumerate(columns)
            if _key(text) == _key(heading)
            and (wanted_group is None or _key(group) == _key(wanted_group))
        ]
        if not matches:
            raise WorkbookProblem("column_missing", column=heading, group=wanted_group or "")
        found[name] = matches[0]

    rows = []
    for number in range(_FIRST_DATA_ROW, sheet.max_row + 1):
        values = [sheet.cell(number, index + 1).value for index in range(width)]
        if all(value is None or text_of(value) == "" for value in values):
            continue
        rows.append(
            SourceRow(
                number=number,
                cells={name: values[index] for name, index in found.items()},
                headings={name: columns[index][0] for name, index in found.items()},
            )
        )
    return rows


@dataclass
class StaffEntry:
    name_in_workbook: str
    full_name: str | None
    email: str | None
    writes: bool
    release_count: int


@dataclass
class UnitEntry:
    key: str
    name_en: str
    name_ja: str | None
    short_label: str | None
    aliases: list[str]
    active: bool


@dataclass
class FieldEntry:
    name_en: str
    name_ja: str | None
    unit_keys: list[str]


@dataclass
class TwoNameEntry:
    code: str
    corresponding: str
    also_featured: str | None


@dataclass
class Intake:
    staff: list[StaffEntry] = field(default_factory=list)
    units: list[UnitEntry] = field(default_factory=list)
    fields: list[FieldEntry] = field(default_factory=list)
    two_names: dict[str, TwoNameEntry] = field(default_factory=dict)


def _table(workbook: Any, sheet_name: str, headings: dict[str, str]) -> list[dict[str, Any]]:
    """Rows of a sheet with headings in row 1, by our names. Headings match by their start."""
    if sheet_name not in workbook.sheetnames:
        raise WorkbookProblem("sheet_missing", sheet=sheet_name)
    sheet = workbook[sheet_name]
    top = [_key(cell.value) for cell in sheet[1]]
    places: dict[str, int] = {}
    for name, heading in headings.items():
        place = next((i for i, text in enumerate(top) if text.startswith(_key(heading))), None)
        if place is None:
            raise WorkbookProblem("column_missing", column=heading, group=sheet_name)
        places[name] = place
    rows = []
    for row in sheet.iter_rows(min_row=2, values_only=True):
        cells = {name: row[place] if place < len(row) else None for name, place in places.items()}
        filled = [value for value in row if value is not None and text_of(value)]
        # A note under the table: one long sentence in the first cell.
        if not filled or (len(filled) == 1 and len(text_of(filled[0])) > 40):
            continue
        rows.append(cells)
    return rows


def _yes(value: Any) -> bool:
    return _key(value) in ("y", "yes", "はい", "true", "1")


def intake(content: bytes) -> Intake:
    workbook = open_workbook(content, "intake")
    result = Intake()
    for row in _table(
        workbook,
        "Staff",
        {
            "name": "Name in workbook",
            "count": "Releases in workbook",
            "full_name": "Full name",
            "email": "Email",
            "writes": "Writes releases",
        },
    ):
        name = text_of(row["name"])
        if not name:
            continue
        count = row["count"]
        result.staff.append(
            StaffEntry(
                name_in_workbook=name,
                full_name=text_of(row["full_name"]) or None,
                email=text_of(row["email"]).lower() or None,
                writes=_yes(row["writes"]),
                release_count=count if isinstance(count, int) else 0,
            )
        )
    for row in _table(
        workbook,
        "Units",
        {
            "key": "Value in workbook",
            "name_en": "Official name (EN)",
            "name_ja": "Name (JA)",
            "short_label": "Short label",
            "aliases": "Aliases",
            "active": "Active",
        },
    ):
        key, name_en = text_of(row["key"]), text_of(row["name_en"])
        if not key or not name_en:
            continue
        result.units.append(
            UnitEntry(
                key=key,
                name_en=name_en,
                name_ja=text_of(row["name_ja"]) or None,
                short_label=text_of(row["short_label"]) or None,
                aliases=[
                    alias
                    for alias in (text_of(part) for part in str(row["aliases"] or "").split(","))
                    if alias
                ],
                active=_yes(row["active"]) if row["active"] is not None else True,
            )
        )
    for row in _table(
        workbook,
        "Fields",
        {"name_en": "Field (EN)", "name_ja": "Field (JA)", "scope": "Scope"},
    ):
        name_en = text_of(row["name_en"])
        if not name_en:
            continue
        result.fields.append(
            FieldEntry(
                name_en=name_en,
                name_ja=text_of(row["name_ja"]) or None,
                unit_keys=[
                    text_of(line) for line in str(row["scope"] or "").splitlines() if line.strip()
                ],
            )
        )
    for row in _table(
        workbook,
        "Two-name releases",
        {
            "code": "ID",
            "proposed": "Proposed corresponding",
            "override": "Override",
            "also": "Also featured",
        },
    ):
        code = text_of(row["code"])
        if not code or re.search(r"\s", code):
            continue
        corresponding = text_of(row["override"]) or text_of(row["proposed"])
        if corresponding:
            result.two_names[code] = TwoNameEntry(
                code=code,
                corresponding=corresponding,
                also_featured=text_of(row["also"]) or None,
            )
    return result
