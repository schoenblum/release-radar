"""The import's review report (BRIEF step 1.8): what was read, and how, in Markdown and CSV.

Entries say what happened to one cell or row. "check" entries are the ones to look at;
"dash" entries list every dash, so exceptions to the dash rule can be spotted; "info"
entries are the other coercions.
"""

import csv
import io
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from app.i18n import t

Level = Literal["check", "dash", "info"]
# The summary's order: the releases first, then what came with them.
COUNT_ORDER = (
    "releases_in_workbook",
    "releases_skipped",
    "releases_new",
    "releases_updated",
    "releases_unchanged",
    "values",
    "dashes",
    "website_off_domain",
    "crossref_found",
    "crossref_not_found",
    "crossref_unavailable",
    "researchers_new",
    "researchers_incomplete",
    "researchers_linked",
    "writers_new",
    "writers_linked",
    "units_new",
    "fields_new",
    "personal_fields_new",
    "trimmed",
    # Researcher feedback (step 2.1).
    "feedback_rows",
    "feedback_skipped",
    "feedback_already",
    "feedback_new",
    "feedback_linked",
    "feedback_not_linked",
    "feedback_releases",
    "feedback_corrected",
    "feedback_other_texts",
)
_LEVELS: tuple[Level, ...] = ("check", "dash", "info")
# The sections each kind of import reports. Feedback has no dash rule.
_SECTIONS: dict[str, tuple[Level, ...]] = {"workbook": _LEVELS, "feedback": ("check", "info")}
_VALUE_LIMIT = 200


@dataclass
class Entry:
    level: Level
    row: int | None
    code: str | None
    column: str | None
    value: str | None
    kind: str
    params: dict[str, Any] = field(default_factory=dict)

    def message(self, language: str) -> str:
        return t(language, f"import.report.{self.kind}", **self.params)

    def stored(self) -> dict[str, Any]:
        """As kept in the import history: plain JSON, read back by ``Report.from_stored``."""
        return {
            "level": self.level,
            "row": self.row,
            "code": self.code,
            "column": self.column,
            "value": self.value,
            "kind": self.kind,
            "params": {name: _plain(value) for name, value in self.params.items()},
        }


def _plain(value: Any) -> Any:
    return value if value is None or isinstance(value, str | int | float | bool) else str(value)


def _shown(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        value = value.date().isoformat() if value.time() == datetime.min.time() else value
    text = str(value).replace("\r", " ").replace("\n", "\\n")
    return text if len(text) <= _VALUE_LIMIT else text[: _VALUE_LIMIT - 1] + "…"


@dataclass
class Report:
    entries: list[Entry] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    # What was imported: "workbook" (step 1.8) or "feedback" (step 2.1).
    kind: str = "workbook"

    @classmethod
    def from_stored(
        cls, counts: dict[str, int], entries: list[dict[str, Any]], kind: str = "workbook"
    ) -> "Report":
        return cls(entries=[Entry(**entry) for entry in entries], counts=dict(counts), kind=kind)

    def add(
        self,
        level: Level,
        kind: str,
        *,
        row: int | None = None,
        code: str | None = None,
        column: str | None = None,
        value: Any = None,
        **params: Any,
    ) -> None:
        self.entries.append(Entry(level, row, code, column, _shown(value), kind, params))

    def count(self, name: str, by: int = 1) -> None:
        self.counts[name] = self.counts.get(name, 0) + by

    def summary(self, language: str) -> list[tuple[str, int]]:
        """The counts in order, labelled in the chosen language. Zeros are left out."""
        return [
            (t(language, f"import.counts.{name}"), self.counts[name])
            for name in COUNT_ORDER
            if self.counts.get(name)
        ]

    def level_counts(self) -> dict[str, int]:
        return {level: sum(1 for e in self.entries if e.level == level) for level in _LEVELS}

    def to_csv(self, language: str) -> str:
        """UTF-8 text; the router adds the byte-order mark so Excel reads it right."""
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\r\n")
        writer.writerow(
            [
                t(language, f"import.columns.{name}")
                for name in ("level", "row", "code", "column", "value", "outcome")
            ]
        )
        for entry in self.entries:
            writer.writerow(
                [
                    t(language, f"import.levels.{entry.level}"),
                    entry.row or "",
                    entry.code or "",
                    entry.column or "",
                    _guard(entry.value or ""),
                    entry.message(language),
                ]
            )
        return buffer.getvalue()

    def to_markdown(self, language: str, *, committed: bool, when: str, who: str) -> str:
        prefix = "" if self.kind == "workbook" else f"{self.kind}_"
        lines = [
            "# "
            + t(
                language,
                f"import.md.{prefix}title_commit"
                if committed
                else f"import.md.{prefix}title_dry_run",
            ),
            "",
            t(language, "import.md.made", when=when, who=who),
            "",
            "## " + t(language, "import.md.summary"),
            "",
        ]
        for label, number in self.summary(language):
            lines.append(f"- {label}: {number}")
        for level in _SECTIONS.get(self.kind, _LEVELS):
            chosen = [entry for entry in self.entries if entry.level == level]
            lines += ["", f"## {t(language, f'import.md.section_{level}')} ({len(chosen)})", ""]
            if not chosen:
                lines.append(t(language, "import.md.none"))
                continue
            headings = [
                t(language, f"import.columns.{name}")
                for name in ("row", "code", "column", "value", "outcome")
            ]
            lines.append("| " + " | ".join(headings) + " |")
            lines.append("|" + "---|" * len(headings))
            for entry in chosen:
                cells = [
                    str(entry.row or ""),
                    entry.code or "",
                    entry.column or "",
                    f"`{entry.value}`" if entry.value else "",
                    entry.message(language),
                ]
                lines.append("| " + " | ".join(_cell(cell) for cell in cells) + " |")
        return "\n".join(lines) + "\n"


def _cell(text: str) -> str:
    return text.replace("|", "\\|")


def _guard(text: str) -> str:
    # A spreadsheet would run these as formulas.
    return f"'{text}" if text.startswith(("=", "+", "-", "@")) and text not in ("-",) else text
