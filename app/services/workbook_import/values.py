"""Reading the old workbook's cells, which mix numbers, dates and text (step 1.8).

Each reader returns the value and what it took to get it, so the report can list every
coercion. A dash is the team's "does not apply" (the dash rule), never a number.
"""

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

# How a value was read. "native": the cell already held it. "text": parsed from text.
How = Literal["native", "text", "dash", "empty", "invalid"]
DASHES = frozenset({"-", "–", "—", "ー", "－"})

_MONTHS = {
    name: number
    for number, names in enumerate(
        (
            ("jan", "january"),
            ("feb", "february"),
            ("mar", "march"),
            ("apr", "april"),
            ("may",),
            ("jun", "june"),
            ("jul", "july"),
            ("aug", "august"),
            ("sep", "sept", "september"),
            ("oct", "october"),
            ("nov", "november"),
            ("dec", "december"),
        ),
        start=1,
    )
    for name in names
}
# 4-March-26, 9-Apr-26, 23-Jan-2026, 4 March 2026
_DAY_MONTH_YEAR = re.compile(r"^(\d{1,2})[\s\-/.]+([a-z]+)\.?[\s\-/.,]+(\d{2}|\d{4})$")
_YEAR_MONTH_DAY = re.compile(r"^(\d{4})[\-/.年](\d{1,2})[\-/.月](\d{1,2})日?$")
_CLOCK = re.compile(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$")
_NUMBER = re.compile(r"^\d{1,3}(,\d{3})+(\.\d+)?$|^\d+(\.\d+)?$")


@dataclass(frozen=True)
class Read[T]:
    value: T | None
    how: How

    @property
    def usable(self) -> bool:
        return self.how in ("native", "text")


def text_of(cell: Any) -> str:
    """A cell as tidy text: NFKC, trimmed, inner runs of space made one."""
    if cell is None:
        return ""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(cell))).strip()


# Written out, it means the same as a dash.
_NOT_APPLICABLE = frozenset({"n/a", "n.a.", "na"})


def is_dash(cell: Any) -> bool:
    if not isinstance(cell, str):
        return False
    text = cell.strip()
    return text in DASHES or text.lower() in _NOT_APPLICABLE


def read_text(cell: Any) -> Read[str]:
    if is_dash(cell):
        return Read(None, "dash")
    text = text_of(cell)
    return Read(text, "native") if text else Read(None, "empty")


def read_date(cell: Any) -> Read[date]:
    if isinstance(cell, datetime):
        return Read(cell.date(), "native")
    if isinstance(cell, date):
        return Read(cell, "native")
    if cell is None or (isinstance(cell, str) and not cell.strip()):
        return Read(None, "empty")
    if is_dash(cell):
        return Read(None, "dash")
    if not isinstance(cell, str):
        return Read(None, "invalid")
    text = text_of(cell).lower()
    try:
        if found := _YEAR_MONTH_DAY.match(text):
            year, month, day = (int(part) for part in found.groups())
            return Read(date(year, month, day), "text")
        if found := _DAY_MONTH_YEAR.match(text):
            day, month_name, year_text = found.groups()
            month = _MONTHS.get(month_name)
            if month is None:
                return Read(None, "invalid")
            year = int(year_text) + (2000 if len(year_text) == 2 else 0)
            return Read(date(year, month, int(day)), "text")
    except ValueError:
        return Read(None, "invalid")
    return Read(None, "invalid")


def read_time(cell: Any) -> Read[time]:
    if isinstance(cell, datetime):
        return Read(cell.time().replace(second=0, microsecond=0), "native")
    if isinstance(cell, time):
        return Read(cell.replace(second=0, microsecond=0, tzinfo=None), "native")
    if cell is None or (isinstance(cell, str) and not cell.strip()):
        return Read(None, "empty")
    if is_dash(cell):
        return Read(None, "dash")
    found = _CLOCK.match(text_of(cell)) if isinstance(cell, str) else None
    if not found:
        return Read(None, "invalid")
    hours, minutes = int(found.group(1)), int(found.group(2))
    if hours > 23 or minutes > 59:
        return Read(None, "invalid")
    return Read(time(hours, minutes), "text")


def read_count(cell: Any) -> Read[Decimal]:
    """A number of views, clicks or a score. Dates and spreadsheet errors are not numbers."""
    if isinstance(cell, bool):
        return Read(None, "invalid")
    if isinstance(cell, int | float | Decimal):
        number = Decimal(str(cell))
        return Read(number, "native") if number >= 0 else Read(None, "invalid")
    if cell is None or (isinstance(cell, str) and not cell.strip()):
        return Read(None, "empty")
    if is_dash(cell):
        return Read(None, "dash")
    if not isinstance(cell, str):
        return Read(None, "invalid")
    text = text_of(cell)
    if not _NUMBER.match(text):
        return Read(None, "invalid")
    try:
        return Read(Decimal(text.replace(",", "")), "text")
    except InvalidOperation:
        return Read(None, "invalid")


def read_gender(cell: Any) -> Read[str]:
    """M or F as the workbook records them. A dash or nothing is not recorded."""
    text = text_of(cell).upper()
    if not text:
        return Read(None, "empty")
    if text in DASHES:
        return Read(None, "dash")
    if text in ("M", "F"):
        return Read(text, "native" if str(cell) == text else "text")
    return Read(None, "invalid")


def normalised_name(name: str) -> str:
    """For matching only: case, width and spacing aside."""
    return text_of(name).casefold()


_SEPARATOR = re.compile(r"\s+and\s+|\s*,\s*|\s*、\s*|\s*&\s*", re.IGNORECASE)


def split_names(text: str) -> tuple[str, list[str]]:
    """The first-listed name, and the others."""
    names = [part for part in (text_of(piece) for piece in _SEPARATOR.split(text)) if part]
    if not names:
        return "", []
    return names[0], names[1:]


_TOP_PAGE = re.compile(r"\b(ea\s+(front|top)\s+page|top\s+spot)\b", re.IGNORECASE)
_TOP_SPOT = re.compile(r"\btop\s+spot(?:\s*no\.?\s*(\d+))?", re.IGNORECASE)


def top_page(notes: str) -> tuple[bool, int | None]:
    """'EA front page', 'EA top page' or 'Top spot': on the top page. 'Top spot No.2': place 2."""
    if not _TOP_PAGE.search(notes):
        return False, None
    spot = _TOP_SPOT.search(notes)
    if spot is None:
        return True, None
    return True, int(spot.group(1)) if spot.group(1) else 1
