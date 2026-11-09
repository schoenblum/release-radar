"""Import of researcher feedback from a Microsoft Forms export (R8.1.2, phase-2 brief §3.2).

Same pattern as the workbook import (step 1.8): the run happens in the open transaction and the
router commits it or rolls it back, so a check reports exactly what Import will do. Re-runnable:
a response is found again by the export's ``Id`` and left as it is, so a fresh export adds only
the new responses.

Columns are found by their heading where they have one. The inquiries question is headed just
``1`` in the export, so it is found by its content. The report says which column was read as
what. Respondent names are stored on the response for the office's record only; the report
never names anyone.
"""

import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.institution import Institution
from app.models.release import Release
from app.models.survey import SOURCE_LEGACY, SurveyResponse
from app.models.user import User
from app.services import audit
from app.services.feedback.template import (
    ACTIVITIES,
    COMMENTS,
    INQUIRIES,
    INVERTED_IDS,
    SATISFACTION,
    SCALE,
    SKIPPED_IDS,
    ensure_template,
    items_of,
)
from app.services.workbook_import.report import Report
from app.services.workbook_import.sheets import WorkbookProblem, open_workbook
from app.services.workbook_import.values import text_of

NOTE_IMPORT = "feedback_import"
NOTE_CORRECTED = "inverted_scale_corrected"
SATISFACTION_KEYS = tuple(item.key for item in items_of(SATISFACTION))

# Our name for a column, and how its heading reads (lower case). First match wins, and a name
# is taken once, so the order matters: the activities question mentions inquiries too.
_RULES: tuple[tuple[str, Any], ...] = (
    ("id", lambda h: h == "id"),
    ("started", lambda h: h.startswith("start time")),
    ("completed", lambda h: h.startswith("completion time")),
    ("email", lambda h: h in {"email", "e-mail"}),
    ("name", lambda h: h == "name"),
    ("language", lambda h: h == "language"),
    ("release_ref", lambda h: "release id" in h),
    ("release_date", lambda h: "date of release" in h),
    ("respondent", lambda h: "first author" in h or "primary researcher" in h),
    ("activities", lambda h: "activit" in h),
    ("inquiries", lambda h: "inquir" in h),
    ("sat_process", lambda h: "production process" in h),
    ("sat_accuracy", lambda h: "conveyed my research" in h),
    ("sat_understandability", lambda h: "well written" in h),
    ("comments", lambda h: "comment" in h),
)
REQUIRED = ("id", "release_ref", "inquiries", "activities", *SATISFACTION_KEYS)
# Read but not used: the address column says "anonymous", the name column is empty, and the
# release is found by its ID, not by a date.
IGNORED = frozenset({"email", "name", "started", "release_date"})
# What the report calls each column, in the import's language (import.feedback_columns.*).
_INVISIBLE = re.compile(r"[​-‏‪-‮⁠﻿]")


@dataclass
class Column:
    index: int
    letter: str
    heading: str
    how: str


def _letter(index: int) -> str:
    name = ""
    index += 1
    while index:
        index, rest = divmod(index - 1, 26)
        name = chr(65 + rest) + name
    return name


def _clean(cell: Any) -> str:
    return _INVISIBLE.sub("", text_of(cell)).strip()


def find_columns(heading: list[Any], rows: list[list[Any]]) -> dict[str, Column]:
    columns: dict[str, Column] = {}
    for index, raw in enumerate(heading):
        lowered = _clean(raw).casefold()
        if not lowered:
            continue
        for name, rule in _RULES:
            if name not in columns and rule(lowered):
                columns[name] = Column(index, _letter(index), _clean(raw), "heading")
                break
    if "inquiries" not in columns:
        # Headed "1" in the export: the column whose answers are the inquiry options.
        labels = {
            item.legacy.casefold()
            for item in items_of(INQUIRIES)
            if item.legacy and not item.exclusive
        }
        taken = {column.index for column in columns.values()}
        best: tuple[int, float] | None = None
        for index in range(len(heading)):
            if index in taken:
                continue
            values = [row[index] for row in rows if index < len(row) and _clean(row[index])]
            if not values:
                continue
            hits = sum(
                1
                for value in values
                if any(token.strip().casefold() in labels for token in str(value).split(";"))
            )
            share = hits / len(values)
            if share >= 0.3 and (best is None or share > best[1]):
                best = (index, share)
        if best is not None:
            columns["inquiries"] = Column(
                best[0], _letter(best[0]), _clean(heading[best[0]]), "content"
            )
    return columns


def read_rows(content: bytes) -> tuple[list[Any], list[list[Any]]]:
    workbook = open_workbook(content, "feedback")
    sheet = workbook.worksheets[0]
    rows = [list(row) for row in sheet.iter_rows(values_only=True)]
    if not rows:
        raise WorkbookProblem("column_missing", column="Id", group=sheet.title)
    return rows[0], rows[1:]


def canonical_code(text: str) -> str:
    """A release ID as people write it, comparable with the stored code: AY2025-011, AY2025-11
    and "AY2025-11)" are the same release."""
    tidy = _clean(text).upper().strip(" ).,;:(")
    return re.sub(r"\d+", lambda match: str(int(match.group())), re.sub(r"\s+", "", tidy))


def _url_key(url: str) -> str:
    return _clean(url).rstrip("/").lower().replace("http://", "https://")


def _language(cell: Any) -> str | None:
    text = _clean(cell).casefold()
    if text.startswith("english") or text == "en":
        return "en"
    if text.startswith("日本語") or text.startswith("japanese") or text == "ja":
        return "ja"
    return None


@dataclass
class Choices:
    answers: dict[str, bool] | None
    other: str | None
    none_with_others: bool = False


def read_choices(cell: Any, question: str) -> Choices:
    """A multiple-choice answer: every option of the question, ticked or not, and what was
    written in "other". An empty cell means the question was skipped: missing, never 0."""
    tokens = [token.strip() for token in _clean(cell).split(";") if token.strip()]
    if not tokens:
        return Choices(None, None)
    options = items_of(question)
    known = {item.legacy.casefold(): item for item in options if item.legacy}
    ticked: set[str] = set()
    others: list[str] = []
    for token in tokens:
        item = known.get(token.casefold())
        if item is None:
            others.append(token)
        else:
            ticked.add(item.key)
    exclusive = {item.key for item in options if item.exclusive}
    return Choices(
        {item.key: item.key in ticked for item in options},
        "; ".join(others) or None,
        none_with_others=bool(ticked & exclusive) and bool(ticked - exclusive),
    )


@dataclass
class _Counts:
    releases: set[uuid.UUID] = field(default_factory=set)


async def run_import(
    db: AsyncSession, institution: Institution, user: User, content: bytes
) -> Report:
    """Read the export and add its new responses. The caller commits or rolls back."""
    report = Report(kind="feedback")
    heading, rows = read_rows(content)
    columns = find_columns(heading, rows)
    labels = {
        "id": "Id",
        "release_ref": "Press release ID",
        "inquiries": "1",
        "activities": "Did any of the following activities result …",
        **{key: key for key in SATISFACTION_KEYS},
    }
    for name in REQUIRED:
        if name not in columns:
            raise WorkbookProblem("column_missing", column=labels[name], group="")
    for name, column in sorted(columns.items(), key=lambda pair: pair[1].index):
        report.add(
            "info",
            "feedback_column_ignored" if name in IGNORED else f"feedback_column_by_{column.how}",
            column=f"{column.letter}: {column.heading}"[:120],
            what=name,
        )

    audit.set_note(db, NOTE_IMPORT)
    template = await ensure_template(db, institution.id)
    timezone = ZoneInfo(institution.timezone)
    existing = {
        response.external_id: response
        for response in await db.scalars(
            select(SurveyResponse).where(
                SurveyResponse.institution_id == institution.id,
                SurveyResponse.source == SOURCE_LEGACY,
            )
        )
    }
    releases = list(
        await db.scalars(select(Release).where(Release.institution_id == institution.id))
    )
    by_code = {canonical_code(release.code): release for release in releases if release.code}
    by_url = {_url_key(release.ea_url): release for release in releases if release.ea_url}
    counts = _Counts(
        releases={response.release_id for response in existing.values() if response.release_id}
    )

    def cell(row: list[Any], name: str) -> Any:
        column = columns.get(name)
        return row[column.index] if column is not None and column.index < len(row) else None

    for offset, row in enumerate(rows):
        number = offset + 2
        external_id = _clean(cell(row, "id"))
        if not external_id:
            continue
        external_id = external_id.removesuffix(".0")
        report.count("feedback_rows")
        if external_id in SKIPPED_IDS:
            report.add("info", f"feedback_skipped_{SKIPPED_IDS[external_id]}", row=number)
            report.count("feedback_skipped")
            continue
        if external_id in existing:
            report.count("feedback_already")
            continue

        reference = _clean(cell(row, "release_ref"))
        release = None
        if reference.lower().startswith("http"):
            release = by_url.get(_url_key(reference))
            if release is not None:
                report.add(
                    "info",
                    "feedback_linked_by_url",
                    row=number,
                    code=release.code,
                    value=reference,
                )
        elif reference:
            release = by_code.get(canonical_code(reference))
            if release is not None and release.code != reference:
                report.add(
                    "info",
                    "feedback_reference_read_as",
                    row=number,
                    code=release.code,
                    value=reference,
                    release=release.code,
                )
        code = release.code if release is not None else (reference or None)
        if release is None:
            report.add("check", "feedback_not_linked", row=number, code=code, value=reference)
            report.count("feedback_not_linked")
        else:
            report.count("feedback_linked")
            counts.releases.add(release.id)
            if release.deleted_at is not None:
                report.add("check", "feedback_release_removed", row=number, code=code)

        answers: dict[str, Any] = {}
        others: dict[str, str] = {}
        for question in (INQUIRIES, ACTIVITIES):
            read = read_choices(cell(row, question), question)
            if read.answers is not None:
                answers.update(read.answers)
            if read.other:
                others[question] = read.other
                report.add(
                    "info",
                    "feedback_other_text",
                    row=number,
                    code=code,
                    value=read.other,
                    question=question,
                )
                report.count("feedback_other_texts")
            if read.none_with_others:
                report.add(
                    "check", "feedback_none_with_others", row=number, code=code, question=question
                )
        for key in SATISFACTION_KEYS:
            raw = _clean(cell(row, key))
            if not raw:
                continue
            score = SCALE.get(raw.casefold())
            if score is None:
                report.add("check", "feedback_scale_unknown", row=number, code=code, value=raw)
            else:
                answers[key] = score
        comment = _clean(cell(row, COMMENTS)) if "comments" in columns else ""
        if comment:
            answers[COMMENTS] = str(cell(row, COMMENTS)).strip()

        language = _language(cell(row, "language"))
        if language is None and _clean(cell(row, "language")):
            report.add(
                "check",
                "feedback_language_unknown",
                row=number,
                code=code,
                value=_clean(cell(row, "language")),
            )
        completed = cell(row, "completed")
        submitted = (
            completed.replace(tzinfo=timezone).astimezone(UTC)
            if isinstance(completed, datetime)
            else None
        )
        respondent = _clean(cell(row, "respondent")) or None

        response = SurveyResponse(
            institution_id=institution.id,
            template_id=template.id,
            release_id=release.id if release is not None else None,
            source=SOURCE_LEGACY,
            external_id=external_id,
            submitted_at=submitted,
            language=language,
            respondent_name=respondent,
            answers=answers,
            other_texts=others,
        )
        db.add(response)
        await db.flush()
        report.count("feedback_new")

        all_low = all(answers.get(key) == 1 for key in SATISFACTION_KEYS)
        if external_id in INVERTED_IDS:
            if all_low:
                # Recorded as its own change, so the response's history shows what the file said.
                audit.set_note(db, NOTE_CORRECTED)
                response.answers = {**answers, **dict.fromkeys(SATISFACTION_KEYS, 5)}
                await db.flush()
                audit.set_note(db, NOTE_IMPORT)
                report.add("info", "feedback_corrected", row=number, code=code, id=external_id)
                report.count("feedback_corrected")
            else:
                report.add(
                    "check", "feedback_correction_not_needed", row=number, code=code, id=external_id
                )
        elif all_low:
            report.add("check", "feedback_all_disagree", row=number, code=code, id=external_id)

    report.counts["feedback_releases"] = len(counts.releases)
    audit.set_note(db, None)
    return report
