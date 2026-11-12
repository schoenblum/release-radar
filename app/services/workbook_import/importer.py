"""Imports the NU workbook into Release Radar (BRIEF step 1.8).

The same code runs for a dry run and for the real thing: a dry run does all the work inside
the transaction and then rolls it back, so its report is exactly what an import would do.

Idempotent: a release is found again by its code, the second "AY2025-42" by its EurekAlert
link. Running it again sets what the workbook says and never clears what it leaves empty.
Lists (fields, units, writers) are only added to or filled in; Settings owns them after that.
A release that already has a researcher keeps it, so merges and splits made in the app hold.
"""

import asyncio
import re
import time as clock
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from datetime import time as time_of_day
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AuditLog,
    Checkpoint,
    CustomField,
    Institution,
    Measure,
    Reading,
    Release,
    Researcher,
    ResearchField,
    Unit,
    User,
    Writer,
)
from app.services import audit, crossref, time_zones
from app.services.field_patch import set_versioned
from app.services.readings import (
    SOURCE_MANUAL,
    STATE_MISSING,
    STATE_NOT_APPLICABLE,
    STATE_VALUE,
    measure_applies,
    on_domain,
)
from app.services.release_codes import _numbering, academic_year, format_code
from app.services.release_types import default_release_type_id
from app.services.workbook_import import sheets
from app.services.workbook_import.report import Level, Report
from app.services.workbook_import.values import (
    Read,
    normalised_name,
    read_count,
    read_date,
    read_gender,
    read_text,
    read_time,
    split_names,
    text_of,
    top_page,
)

# The workbook's own numbers, by column, and the measure each goes to (BRIEF step 1.8).
MEASURE_COLUMNS = {
    "ea_views_d0": "ea_views.d0",
    "ea_views_d28": "ea_views.d28",
    "altmetric_d0": "altmetric.d0",
    "altmetric_d28": "altmetric.d28",
}
# Personal fields seeded from the workbook (BRIEF §6.6): label, type, due checkpoint.
# Their owners are chosen at import time, so no one's name lives in the code.
PERSONAL_FIELDS = {
    "bitly": ("Bitly clicks, 28 days", "integer", "d28"),
    "pitches": ("Pitches", "integer", None),
    "request_received": ("Request received", "date", None),
}
_DECIMAL_UNITS = frozenset({"score"})
_READING_LIMIT = Decimal("1e12")
_CROSSREF_AT_ONCE = 4
_CROSSREF_KEEP_SECONDS = 3600
_crossref_cache: dict[str, tuple[float, crossref.Lookup]] = {}
_JAPANESE = re.compile(r"[぀-ヿ㐀-鿿]")
AUDIT_NOTE = "workbook_import"


@dataclass
class Files:
    release_list: bytes
    intake: bytes


async def look_up_papers(dois: set[str], contact_email: str | None) -> dict[str, crossref.Lookup]:
    """Every DOI at Crossref, a few at a time. A dry run's answers serve the import after it."""
    gate = asyncio.Semaphore(_CROSSREF_AT_ONCE)
    now = clock.monotonic()

    async def one(doi: str) -> tuple[str, crossref.Lookup]:
        kept = _crossref_cache.get(doi)
        if kept and now - kept[0] < _CROSSREF_KEEP_SECONDS:
            return doi, kept[1]
        async with gate:
            answer = await crossref.lookup(doi, contact_email)
        if answer.status != crossref.UNAVAILABLE:
            _crossref_cache[doi] = (clock.monotonic(), answer)
        return doi, answer

    return dict(await asyncio.gather(*(one(doi) for doi in sorted(dois))))


def _author_family(author: dict[str, Any]) -> str:
    if author.get("family"):
        return normalised_name(author["family"])
    name = text_of(author.get("name"))
    return normalised_name(name.split()[-1]) if name else ""


@dataclass
class _Planned:
    release: Release
    row: int
    code: str
    heading: str
    measure_key: str
    read: Read[Decimal]
    cell: Any


@dataclass
class _Importer:
    db: AsyncSession
    institution: Institution
    user: User
    intake: sheets.Intake
    papers: dict[str, crossref.Lookup]
    owners: dict[str, uuid.UUID | None]
    report: Report = field(default_factory=Report)
    units: dict[str, Unit] = field(default_factory=dict)
    unit_keys: set[str] = field(default_factory=set)
    writers: dict[str, Writer] = field(default_factory=dict)
    researchers: dict[tuple[str, uuid.UUID | None], Researcher] = field(default_factory=dict)
    known_researchers: set[uuid.UUID] = field(default_factory=set)
    personal: dict[str, CustomField] = field(default_factory=dict)
    planned: list[_Planned] = field(default_factory=list)
    # Brief §3.4, the catch-up before D1: releases already in Release Radar get only what is
    # empty or missing there. Nothing already there changes, and every difference is listed.
    fill_empty_only: bool = False
    # Releases this run made: they get everything, as in any import.
    fresh: set[uuid.UUID] = field(default_factory=set)
    # What a record is called, for the report: writers, units, fields, researchers.
    names: dict[uuid.UUID, str] = field(default_factory=dict)
    # The row being read: its number, code and headings.
    here: tuple[int, str, dict[str, str]] = (0, "", {})

    # ------------------------------------------------------------ lists

    async def fields_and_units(self) -> None:
        institution_id = self.institution.id
        fields = {
            normalised_name(row.name_en): row
            for row in await self.db.scalars(
                select(ResearchField).where(ResearchField.institution_id == institution_id)
            )
        }
        field_for_unit: dict[str, ResearchField] = {}
        for entry in self.intake.fields:
            found = fields.get(normalised_name(entry.name_en))
            if found is None:
                found = ResearchField(
                    institution_id=institution_id,
                    name_en=entry.name_en,
                    name_ja=entry.name_ja,
                    scope_note=", ".join(entry.unit_keys) or None,
                )
                self.db.add(found)
                fields[normalised_name(entry.name_en)] = found
                self.report.count("fields_new")
            elif found.name_ja is None and entry.name_ja:
                found.name_ja = entry.name_ja
            for key in entry.unit_keys:
                field_for_unit[normalised_name(key)] = found
        await self.db.flush()

        existing = list(
            await self.db.scalars(select(Unit).where(Unit.institution_id == institution_id))
        )

        def find(entry: sheets.UnitEntry) -> Unit | None:
            wanted = {normalised_name(entry.key), *(normalised_name(a) for a in entry.aliases)}
            for unit in existing:
                names = {
                    normalised_name(unit.key),
                    normalised_name(unit.name_en),
                    *(normalised_name(alias) for alias in unit.aliases),
                }
                if wanted & names:
                    return unit
            return None

        for entry in self.intake.units:
            research_field = field_for_unit.get(normalised_name(entry.key))
            unit = find(entry)
            if unit is None:
                unit = Unit(
                    institution_id=institution_id,
                    key=entry.key,
                    name_en=entry.name_en,
                    name_ja=entry.name_ja,
                    short_label=entry.short_label,
                    aliases=entry.aliases,
                    is_active=entry.active,
                    default_field_id=research_field.id if research_field else None,
                )
                self.db.add(unit)
                existing.append(unit)
                self.report.count("units_new")
                continue
            # Settings own the lists once they exist: only fill in what is missing.
            if unit.name_ja is None and entry.name_ja:
                unit.name_ja = entry.name_ja
            if unit.short_label is None and entry.short_label:
                unit.short_label = entry.short_label
            if unit.default_field_id is None and research_field is not None:
                unit.default_field_id = research_field.id
            missing = [alias for alias in entry.aliases if alias not in unit.aliases]
            if missing:
                unit.aliases = [*unit.aliases, *missing]
        await self.db.flush()
        for unit in existing:
            for name in (unit.key, unit.name_en, *unit.aliases):
                self.units.setdefault(normalised_name(name), unit)
            self.unit_keys.add(normalised_name(unit.key))
            self.unit_keys.update(normalised_name(alias) for alias in unit.aliases)

    async def writers_from_staff(self) -> None:
        institution_id = self.institution.id
        writers = list(
            await self.db.scalars(select(Writer).where(Writer.institution_id == institution_id))
        )
        users = {
            user.email.lower(): user
            for user in await self.db.scalars(
                select(User).where(User.institution_id == institution_id)
            )
        }
        linked = {writer.user_id for writer in writers if writer.user_id}

        def find(entry: sheets.StaffEntry) -> Writer | None:
            user = users.get(entry.email or "")
            names = {normalised_name(entry.name_in_workbook)}
            if entry.full_name:
                names.add(normalised_name(entry.full_name))
            for writer in writers:
                if user is not None and writer.user_id == user.id:
                    return writer
                known = {normalised_name(writer.display_name_en)}
                if writer.full_name:
                    known.add(normalised_name(writer.full_name))
                if names & known:
                    return writer
            return None

        for entry in self.intake.staff:
            if not (entry.writes or entry.release_count):
                continue
            writer = find(entry)
            if writer is None:
                writer = Writer(
                    institution_id=institution_id,
                    display_name_en=entry.name_in_workbook,
                    full_name=entry.full_name,
                    is_active=entry.writes,
                )
                self.db.add(writer)
                writers.append(writer)
                self.report.count("writers_new")
            elif writer.full_name is None and entry.full_name:
                writer.full_name = entry.full_name
            user = users.get(entry.email or "")
            if user is not None and writer.user_id is None and user.id not in linked:
                writer.user_id = user.id
                linked.add(user.id)
                self.report.count("writers_linked")
            elif user is None and entry.writes:
                self.report.add(
                    "info", "writer_without_account", column="Staff", value=entry.name_in_workbook
                )
        await self.db.flush()
        for writer in writers:
            self.writers.setdefault(normalised_name(writer.display_name_en), writer)
            if writer.full_name:
                self.writers.setdefault(normalised_name(writer.full_name), writer)
        for entry in self.intake.staff:
            writer = self.writers.get(normalised_name(entry.full_name or entry.name_in_workbook))
            if writer is not None:
                self.writers.setdefault(normalised_name(entry.name_in_workbook), writer)

    async def personal_fields(self) -> None:
        institution_id = self.institution.id
        for name, (label, field_type, due) in PERSONAL_FIELDS.items():
            owner_id = self.owners.get(name)
            if owner_id is None:
                self.report.add("check", "personal_field_skipped", column=label)
                continue
            owner = await self.db.scalar(
                select(User).where(User.id == owner_id, User.institution_id == institution_id)
            )
            if owner is None:
                raise sheets.WorkbookProblem("owner_unknown")
            found = await self.db.scalar(
                select(CustomField).where(
                    CustomField.institution_id == institution_id,
                    CustomField.scope == "personal",
                    CustomField.owner_id == owner.id,
                    func.lower(CustomField.label_en) == label.lower(),
                )
            )
            if found is None:
                checkpoint = (
                    await self.db.scalar(
                        select(Checkpoint.id).where(
                            Checkpoint.institution_id == institution_id, Checkpoint.key == due
                        )
                    )
                    if due
                    else None
                )
                position = await self.db.scalar(
                    select(func.coalesce(func.max(CustomField.position), -1)).where(
                        CustomField.institution_id == institution_id
                    )
                )
                found = CustomField(
                    institution_id=institution_id,
                    key=await self._free_field_key(label),
                    label_en=label,
                    field_type=field_type,
                    scope="personal",
                    owner_id=owner.id,
                    position=position + 1,
                    due_checkpoint_id=checkpoint,
                )
                self.db.add(found)
                await self.db.flush()
                self.report.count("personal_fields_new")
            self.personal[name] = found

    async def _free_field_key(self, label: str) -> str:
        base = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")[:50] or "field"
        taken = set(
            await self.db.scalars(
                select(CustomField.key).where(CustomField.institution_id == self.institution.id)
            )
        )
        key, number = base, 2
        while key in taken:
            key, number = f"{base}_{number}", number + 1
        return key

    async def load_researchers(self) -> None:
        for person in await self.db.scalars(
            select(Researcher).where(
                Researcher.institution_id == self.institution.id,
                Researcher.merged_into_id.is_(None),
            )
        ):
            self.researchers.setdefault(
                (normalised_name(person.name), person.current_unit_id), person
            )
            self.known_researchers.add(person.id)

    # ------------------------------------------------------------ releases

    def _assign(self, release: Release, name: str, value: Any, changed: list[str]) -> None:
        """What the workbook says wins; what it leaves empty never clears anything. A version
        rises with each change, so a screen opened before the import is told. With
        ``fill_empty_only``, only what is empty on an existing release is filled."""
        current = getattr(release, name)
        if value is None or current == value:
            return
        if self.keeps(release):
            if not _is_empty(current):
                self.noted("check", "fill_kept", name, value, current)
                return
            self.noted("info", "fill_filled", name, value, None)
        set_versioned(release, name, value)
        changed.append(name)

    def keeps(self, release: Release) -> bool:
        """Whether this release keeps what it has (fill-only mode, made before this run)."""
        return self.fill_empty_only and release.id not in self.fresh

    def noted(self, level: Level, kind: str, name: str, value: Any, current: Any) -> None:
        number, code, headings = self.here
        self.report.add(
            level,
            kind,
            row=number,
            code=code,
            column=headings.get(_FIELD_COLUMNS.get(name, name), name),
            value=self.shown(value),
            field=name,
            current=self.shown(current) if current is not None else "—",
        )
        self.report.count("cells_filled" if kind == "fill_filled" else "cells_kept")

    def shown(self, value: Any) -> str:
        if isinstance(value, uuid.UUID):
            return self.names.get(value, str(value))
        if isinstance(value, bool):
            return "1" if value else "0"
        if isinstance(value, date | time_of_day):
            return value.isoformat()
        if isinstance(value, Decimal):
            return format(value.normalize(), "f")
        if isinstance(value, list):
            return f"{len(value)}"
        if isinstance(value, dict):
            return str(value.get("value", "N/A"))
        return str(value)

    async def researcher_for(
        self,
        name: str,
        unit: Unit | None,
        authors: list[dict[str, Any]],
        gender: Read[str],
        row: sheets.SourceRow,
        code: str,
    ) -> Researcher:
        heading = row.headings["researcher"]
        given = family = None
        shown = name
        status = "unverified"
        if len(name.split()) == 1 and not _JAPANESE.search(name):
            matches = [a for a in authors if _author_family(a) == normalised_name(name)]
            if len(matches) == 1 and (matches[0].get("given") or matches[0].get("name")):
                given = matches[0].get("given")
                family = matches[0].get("family") or name
                shown = text_of(f"{given or ''} {family}") if given else text_of(matches[0]["name"])
                self.report.add(
                    "info",
                    "researcher_resolved",
                    row=row.number,
                    code=code,
                    column=heading,
                    value=name,
                    name=shown,
                )
            else:
                status = "incomplete"
                self.report.add(
                    "check",
                    "researcher_unresolved",
                    row=row.number,
                    code=code,
                    column=heading,
                    value=name,
                    matches=len(matches),
                )
        unit_id = unit.id if unit else None
        person = self.researchers.get((normalised_name(shown), unit_id))
        if person is None:
            person = Researcher(
                institution_id=self.institution.id,
                name=shown,
                given_name=given,
                family_name=family,
                current_unit_id=unit_id,
                gender=gender.value or "not_recorded",
                status=status,
            )
            self.db.add(person)
            await self.db.flush()
            self.researchers[(normalised_name(shown), unit_id)] = person
            self.report.count("researchers_new")
            if status == "incomplete":
                self.report.count("researchers_incomplete")
            return person
        if person.id in self.known_researchers:
            self.known_researchers.discard(person.id)
            self.report.count("researchers_linked")
        self._gender(person, gender, row, code)
        return person

    def _gender(
        self, person: Researcher, gender: Read[str], row: sheets.SourceRow, code: str
    ) -> None:
        if gender.value is None:
            return
        if person.gender == "not_recorded":
            if self.fill_empty_only and person.id in self.known_researchers:
                self.noted("info", "fill_filled", "gender", gender.value, None)
            set_versioned(person, "gender", gender.value)
        elif person.gender != gender.value:
            self.report.add(
                "check",
                "gender_conflict",
                row=row.number,
                code=code,
                column=row.headings["gender"],
                value=gender.value,
                kept=person.gender,
            )

    async def release_row(
        self, row: sheets.SourceRow, code: str, release: Release | None
    ) -> Release | None:
        cells, headings = row.cells, row.headings
        number = row.number
        add = self.report.add
        self.here = (number, code, headings)

        def heading(name: str) -> str:
            return headings[name]

        title = read_text(cells["title"]).value
        doi_text = read_text(cells["doi"])
        doi = crossref.normalise_doi(doi_text.value) if doi_text.value else None
        if doi_text.how == "dash":
            add(
                "dash",
                "dash_empty",
                row=number,
                code=code,
                column=heading("doi"),
                value=cells["doi"],
            )
        if doi_text.value and doi is None:
            add(
                "check",
                "doi_invalid",
                row=number,
                code=code,
                column=heading("doi"),
                value=cells["doi"],
            )
        elif doi and doi != doi_text.value:
            add(
                "info",
                "doi_normalised",
                row=number,
                code=code,
                column=heading("doi"),
                value=cells["doi"],
                doi=doi,
            )
        if not title and not doi:
            add("check", "skipped_no_title", row=number, code=code)
            self.report.count("releases_skipped")
            return None

        is_new = release is None
        if release is None:
            # A release needs its title or DOI from the start (R7.5.6).
            # R6.4.1: imported releases start as the institution's default type.
            release = Release(
                institution_id=self.institution.id,
                code=code,
                title=title or None,
                doi=doi,
                release_type_id=await default_release_type_id(self.db, self.institution),
            )
            self.db.add(release)
            await self.db.flush()
            self.fresh.add(release.id)
        elif release.deleted_at is not None and self.fill_empty_only:
            # Removed in the app on purpose: the catch-up leaves it so.
            add("check", "fill_removed_left", row=number, code=code)
            self.report.count("releases_unchanged")
            return None
        elif release.deleted_at is not None:
            release.deleted_at = None
            add("check", "release_restored", row=number, code=code)
        changed: list[str] = []
        assign = lambda name, value: self._assign(release, name, value, changed)  # noqa: E731

        assign("title", title)

        writer_text = text_of(cells["writer"])
        writer = self.writers.get(normalised_name(writer_text)) if writer_text else None
        if writer_text and writer is None:
            add(
                "check",
                "writer_unknown",
                row=number,
                code=code,
                column=heading("writer"),
                value=writer_text,
            )
        assign("writer_id", writer.id if writer else None)

        unit_text = text_of(cells["unit"])
        unit = self.units.get(normalised_name(unit_text)) if unit_text else None
        if unit_text and unit is None:
            add(
                "check",
                "unit_unknown",
                row=number,
                code=code,
                column=heading("unit"),
                value=unit_text,
            )
        elif unit is not None and unit_text != unit.key:
            add(
                "info",
                "unit_alias",
                row=number,
                code=code,
                column=heading("unit"),
                value=unit_text,
                unit=unit.key,
            )
        assign("unit_id", unit.id if unit else None)
        if unit is not None and (is_new or release.field_id is None):
            assign("field_id", unit.default_field_id)

        # The paper first: a surname alone is looked up among its authors.
        assign("doi", doi)
        paper = None
        if doi:
            answer = self.papers.get(doi)
            if answer is not None and answer.status == crossref.FOUND:
                paper = answer.paper
                self.report.count("crossref_found")
            else:
                status = answer.status if answer else crossref.UNAVAILABLE
                self.report.count(f"crossref_{status}")
                add(
                    "check",
                    f"crossref_{status}",
                    row=number,
                    code=code,
                    column=heading("doi"),
                    value=doi,
                )
        paper_title = read_text(cells["paper_title"]).value
        assign("paper_title", paper_title or (paper.paper_title if paper else None))
        if paper is not None:
            for name in ("journal", "publication_date"):
                if getattr(release, name) is None:
                    assign(name, getattr(paper, name))
            if not release.authors and paper.authors:
                assign("authors", paper.authors)

        await self._researcher(release, row, code, unit, paper.authors if paper else [], changed)
        self._dates_and_links(release, row, code, changed)
        self._notes(release, row, code, changed)
        self._personal_values(release, row, code, changed)

        for column, key in MEASURE_COLUMNS.items():
            self.planned.append(
                _Planned(
                    release,
                    number,
                    code,
                    heading(column),
                    key,
                    read_count(cells[column]),
                    cells[column],
                )
            )
        if is_new:
            self.report.count("releases_new")
        elif changed:
            self.report.count("releases_updated")
        else:
            self.report.count("releases_unchanged")
        return release

    async def _researcher(
        self,
        release: Release,
        row: sheets.SourceRow,
        code: str,
        unit: Unit | None,
        authors: list[dict[str, Any]],
        changed: list[str],
    ) -> None:
        cells, number = row.cells, row.number
        gender = read_gender(cells["gender"])
        if gender.how == "dash":
            self.report.add(
                "dash",
                "gender_dash",
                row=number,
                code=code,
                column=row.headings["gender"],
                value=cells["gender"],
            )
        elif gender.how == "invalid":
            self.report.add(
                "check",
                "gender_unreadable",
                row=number,
                code=code,
                column=row.headings["gender"],
                value=cells["gender"],
            )
        elif gender.how == "text":
            self.report.count("trimmed")
        if release.researcher_id is not None:
            # Chosen before, perhaps merged or split in the app since: it stays.
            person = await self.db.get(Researcher, release.researcher_id)
            if person is not None:
                self._gender(person, gender, row, code)
                listed = self.intake.two_names.get(code)
                written = (
                    listed.corresponding
                    if listed is not None
                    else split_names(text_of(cells["researcher"]))[0]
                )
                if (
                    self.keeps(release)
                    and written
                    and normalised_name(written) != normalised_name(person.name)
                ):
                    self.noted("check", "fill_kept", "researcher_id", written, person.id)
            return

        listed = self.intake.two_names.get(code)
        if listed is not None:
            name, also = listed.corresponding, listed.also_featured
            self.report.add(
                "info",
                "researcher_from_sheet",
                row=number,
                code=code,
                column=row.headings["researcher"],
                value=cells["researcher"],
                name=name,
            )
        else:
            text = text_of(cells["researcher"])
            if not text:
                self.report.add(
                    "check",
                    "researcher_missing",
                    row=number,
                    code=code,
                    column=row.headings["researcher"],
                )
                return
            name, others = split_names(text)
            also = ", ".join(others) or None
            if others:
                self.report.add(
                    "check",
                    "researcher_first_listed",
                    row=number,
                    code=code,
                    column=row.headings["researcher"],
                    value=text,
                    name=name,
                )
        person = await self.researcher_for(name, unit, authors, gender, row, code)
        self._assign(release, "researcher_id", person.id, changed)
        if also and not release.also_featured:
            self._assign(release, "also_featured", also, changed)

    def _dates_and_links(
        self, release: Release, row: sheets.SourceRow, code: str, changed: list[str]
    ) -> None:
        cells, headings, number = row.cells, row.headings, row.number
        add = self.report.add
        assign = lambda name, value: self._assign(release, name, value, changed)  # noqa: E731

        embargo = read_date(cells["embargo"])
        if embargo.how == "dash":
            add(
                "dash",
                "dash_not_embargoed",
                row=number,
                code=code,
                column=headings["embargo"],
                value=cells["embargo"],
            )
        elif embargo.how == "invalid":
            add(
                "check",
                "embargo_unreadable",
                row=number,
                code=code,
                column=headings["embargo"],
                value=cells["embargo"],
            )
        if embargo.how != "invalid":
            # A date says embargoed; nothing, or a dash, says not.
            assign("embargoed", embargo.usable)

        posted = read_date(cells["release_date"])
        self._note_date(posted, "release_date", row, code, empty_matters=True)
        clock_time = read_time(cells["release_time"])
        # The workbook's dates and times are EurekAlert's, US Eastern; Release Radar keeps
        # them in the institution's time zone, so the date can move by a day.
        day, at = posted.value, clock_time.value
        if day is not None and at is not None:
            day, at = time_zones.convert(day, at, time_zones.EASTERN, self.institution.timezone)
        assign("release_date", day)
        if release.release_date is not None:
            year = academic_year(release.release_date, self.institution.ay_start_month)
            if str(year) not in code:
                add(
                    "info",
                    "code_year_differs",
                    row=number,
                    code=code,
                    column=headings["release_date"],
                    value=release.release_date.isoformat(),
                    year=year,
                )

        if clock_time.how == "text":
            add(
                "info",
                "time_from_text",
                row=number,
                code=code,
                column=headings["release_time"],
                value=cells["release_time"],
                time=clock_time.value.strftime("%H:%M"),
            )
        elif clock_time.how == "invalid":
            add(
                "check",
                "time_unreadable",
                row=number,
                code=code,
                column=headings["release_time"],
                value=cells["release_time"],
            )
        elif clock_time.how == "dash":
            add(
                "dash",
                "dash_empty",
                row=number,
                code=code,
                column=headings["release_time"],
                value=cells["release_time"],
            )
        assign("release_time", at)

        for name in ("ea_url", "website_url"):
            link = read_text(cells[name])
            if link.how == "dash":
                add(
                    "dash",
                    "dash_empty",
                    row=number,
                    code=code,
                    column=headings[name],
                    value=cells[name],
                )
            assign(name, link.value)
        if release.ea_url and not re.match(self.institution.ea_url_pattern, release.ea_url):
            add(
                "check",
                "ea_url_unusual",
                row=number,
                code=code,
                column=headings["ea_url"],
                value=release.ea_url,
            )
        if release.website_url and not on_domain(release, self.institution.website_domain):
            add(
                "info",
                "website_off_domain",
                row=number,
                code=code,
                column=headings["website_url"],
                value=release.website_url,
                domain=self.institution.website_domain or "—",
            )
            self.report.count("website_off_domain")

    def _note_date(
        self, read: Read[date], name: str, row: sheets.SourceRow, code: str, *, empty_matters: bool
    ) -> None:
        add, column, cell = self.report.add, row.headings[name], row.cells[name]
        if read.how == "text":
            add(
                "info",
                "date_from_text",
                row=row.number,
                code=code,
                column=column,
                value=cell,
                date=read.value.isoformat(),
            )
        elif read.how == "invalid":
            add("check", "not_a_date", row=row.number, code=code, column=column, value=cell)
        elif read.how == "dash":
            add("dash", "dash_empty", row=row.number, code=code, column=column, value=cell)
        elif read.how == "empty" and empty_matters:
            add("check", "no_release_date", row=row.number, code=code, column=column)

    def _notes(
        self, release: Release, row: sheets.SourceRow, code: str, changed: list[str]
    ) -> None:
        raw = row.cells["notes"]
        notes = str(raw).strip() if raw is not None and str(raw).strip() else None
        if notes is None:
            return
        self._assign(release, "notes", notes, changed)
        on_top, place = top_page(notes)
        if on_top:
            self._assign(release, "ea_top_page", True, changed)
            self._assign(release, "ea_top_position", place, changed)
            self.report.add(
                "info",
                "top_page",
                row=row.number,
                code=code,
                column=row.headings["notes"],
                value=notes,
                place=place or "—",
            )

    def _personal_values(
        self, release: Release, row: sheets.SourceRow, code: str, changed: list[str]
    ) -> None:
        for name, (_, field_type, _) in PERSONAL_FIELDS.items():
            custom = self.personal.get(name)
            cell = row.cells[name]
            if custom is None or cell is None:
                continue
            column = row.headings[name]
            if field_type == "date":
                read: Read[Any] = read_date(cell)
                self._note_date(read, name, row, code, empty_matters=False)
                stored = read.value.isoformat() if read.usable else None
            else:
                read = read_count(cell)
                if read.how == "text":
                    self.report.add(
                        "info",
                        "number_from_text",
                        row=row.number,
                        code=code,
                        column=column,
                        value=cell,
                        number=read.value,
                    )
                elif read.how == "invalid":
                    self.report.add(
                        "check",
                        "not_a_number",
                        row=row.number,
                        code=code,
                        column=column,
                        value=cell,
                    )
                elif read.how == "dash":
                    self.report.add(
                        "dash", "dash_na", row=row.number, code=code, column=column, value=cell
                    )
                stored = int(read.value) if read.usable else None
            if read.how == "dash":
                value: dict[str, Any] | None = {"state": "not_applicable"}
            elif stored is not None:
                value = {"state": "value", "value": stored}
            else:
                continue
            key = custom.key
            current = release.custom_values.get(key)
            if current != value and self.keeps(release):
                if current is not None:
                    self.noted("check", "fill_kept", name, value, current)
                    continue
                self.noted("info", "fill_filled", name, value, None)
            if current != value:
                release.custom_values = {**release.custom_values, key: value}
                name_key = f"custom_values.{key}"
                release.field_versions = {
                    **release.field_versions,
                    name_key: release.field_versions.get(name_key, 0) + 1,
                }
                changed.append(name_key)

    # ------------------------------------------------------------ readings

    async def readings(self) -> None:
        """After the rules have made each release's readings: the workbook's numbers and dashes."""
        await self.db.flush()
        measures = {
            measure.key: measure
            for measure in await self.db.scalars(
                select(Measure).where(
                    Measure.institution_id == self.institution.id, Measure.is_active.is_(True)
                )
            )
        }
        release_ids = list({plan.release.id for plan in self.planned})
        readings = {
            (reading.release_id, reading.measure_id): reading
            for reading in await self.db.scalars(
                select(Reading).where(Reading.release_id.in_(release_ids))
            )
        }
        now = datetime.now(UTC)
        for plan in self.planned:
            measure = measures.get(plan.measure_key)
            reading = readings.get((plan.release.id, measure.id)) if measure else None
            if reading is None:
                continue
            read, add = plan.read, self.report.add
            where = {"row": plan.row, "code": plan.code, "column": plan.heading}
            self.here = (plan.row, plan.code, {plan.measure_key: plan.heading})
            # In fill-only mode a reading is open only while nothing is there but the rules'.
            keeps = self.keeps(plan.release) and not (
                reading.state == STATE_MISSING or reading.inferred
            )
            if read.how == "dash":
                add("dash", "dash_na", value=plan.cell, **where)
                if keeps:
                    if reading.state != STATE_NOT_APPLICABLE:
                        self.noted("check", "fill_kept", plan.measure_key, "N/A", reading.value)
                    self.report.count("dashes")
                    continue
                if self.keeps(plan.release):
                    self.noted("info", "fill_filled", plan.measure_key, "N/A", None)
                if reading.state != STATE_NOT_APPLICABLE or reading.source != SOURCE_MANUAL:
                    reading.value, reading.state, reading.source = (
                        None,
                        STATE_NOT_APPLICABLE,
                        SOURCE_MANUAL,
                    )
                    reading.inferred = False
                    self._entered(reading, now)
                self.report.count("dashes")
                continue
            if read.how == "invalid":
                serial = _excel_serial(plan.cell)
                if serial is not None:
                    # Excel shows a number formatted as a date as a day early in 1900.
                    add("check", "number_shown_as_date", value=plan.cell, number=serial, **where)
                else:
                    add("check", "not_a_number", value=plan.cell, **where)
                continue
            if not read.usable:
                continue
            number = read.value
            if number >= _READING_LIMIT or (
                measure.unit not in _DECIMAL_UNITS and number != number.to_integral_value()
            ):
                add("check", "not_a_number", value=str(number), **where)
                continue
            if read.how == "text":
                add("info", "number_from_text", value=str(number), number=number, **where)
            if not measure_applies(measure, plan.release, self.institution.website_domain):
                add("check", "value_where_na", value=str(number), **where)
            if keeps:
                if reading.state != STATE_VALUE or reading.value != number:
                    current = reading.value if reading.state == STATE_VALUE else "N/A"
                    self.noted("check", "fill_kept", plan.measure_key, number, current)
                self.report.count("values")
                continue
            if self.keeps(plan.release) and (
                reading.state != STATE_VALUE or reading.value != number or reading.inferred
            ):
                self.noted("info", "fill_filled", plan.measure_key, number, None)
            # A 0 in the workbook was entered by someone, so it replaces an inferred one.
            if reading.state != STATE_VALUE or reading.value != number or reading.inferred:
                reading.value, reading.state, reading.source = number, STATE_VALUE, SOURCE_MANUAL
                reading.inferred = False
                self._entered(reading, now)
            self.report.count("values")

    def _entered(self, reading: Reading, now: datetime) -> None:
        reading.version += 1
        reading.entered_by_id = self.user.id
        reading.entered_at = now


# The workbook column each release field comes from, for the report.
_FIELD_COLUMNS = {
    "writer_id": "writer",
    "unit_id": "unit",
    "field_id": "unit",
    "researcher_id": "researcher",
    "also_featured": "researcher",
    "gender": "gender",
    "journal": "doi",
    "publication_date": "doi",
    "authors": "doi",
    "embargoed": "embargo",
    "release_time": "release_time",
    "ea_top_page": "notes",
    "ea_top_position": "notes",
}


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _excel_serial(cell: Any) -> int | None:
    """The number behind a date in Excel's first years, which is almost always a slip."""
    if not isinstance(cell, datetime) or cell.year > 1900:
        return None
    # Excel counts a 29 February 1900 that never was, so the first two months are a day off.
    epoch = date(1899, 12, 31) if cell.date() < date(1900, 3, 1) else date(1899, 12, 30)
    return (cell.date() - epoch).days


def _year_of(code: str) -> int | None:
    found = re.search(r"(\d{4})", code)
    return int(found.group(1)) if found else None


async def run_import(
    db: AsyncSession,
    institution: Institution,
    user: User,
    files: Files,
    owners: dict[str, uuid.UUID | None],
    *,
    fill_empty_only: bool = False,
) -> Report:
    """Does the whole import in the open transaction. The caller commits or rolls back."""
    rows = sheets.release_rows(files.release_list)
    intake = sheets.intake(files.intake)

    dois = set()
    for row in rows:
        text = read_text(row.cells["doi"]).value
        doi = crossref.normalise_doi(text) if text else None
        if doi:
            dois.add(doi)
    papers = await look_up_papers(dois, institution.contact_email)

    audit.set_actor(db, user.id)
    audit.set_note(db, AUDIT_NOTE)
    work = _Importer(db, institution, user, intake, papers, owners)
    work.fill_empty_only = fill_empty_only
    work.report.counts["releases_in_workbook"] = len(rows)
    if fill_empty_only:
        work.report.add("info", "fill_mode")
    await work.fields_and_units()
    await work.writers_from_staff()
    await work.personal_fields()
    await work.load_researchers()
    for model, label in (
        (Writer, "display_name_en"),
        (Unit, "key"),
        (ResearchField, "name_en"),
        (Researcher, "name"),
    ):
        for row_id, name in await db.execute(
            select(model.id, getattr(model, label)).where(model.institution_id == institution.id)
        ):
            work.names[row_id] = name

    existing = list(
        await db.scalars(select(Release).where(Release.institution_id == institution.id))
    )
    by_code = {release.code: release for release in existing if release.code}
    # Releases an earlier import made. Any other with a workbook code was made in the app.
    imported = set(
        await db.scalars(
            select(AuditLog.entity_id).where(
                AuditLog.institution_id == institution.id,
                AuditLog.entity_type == Release.__tablename__,
                AuditLog.action == "create",
                AuditLog.note == AUDIT_NOTE,
            )
        )
    )
    codes_in_workbook = {text_of(row.cells["code"]) for row in rows}
    pattern = institution.release_code_pattern
    taken: dict[int, set[int]] = {}
    for code in {*by_code, *codes_in_workbook}:
        year = _year_of(code)
        found = _numbering(pattern, year).match(code) if year else None
        if found:
            taken.setdefault(year, set()).add(int(found.group(1)))

    seen: dict[str, int] = {}
    for row in rows:
        code = text_of(row.cells["code"])
        writer_text = normalised_name(text_of(row.cells["writer"]))
        if writer_text and writer_text in work.unit_keys and writer_text not in work.writers:
            work.report.add(
                "check",
                "skipped_unit_writer",
                row=row.number,
                code=code,
                column=row.headings["writer"],
                value=row.cells["writer"],
            )
            work.report.count("releases_skipped")
            continue
        if not code:
            work.report.add("check", "skipped_no_code", row=row.number)
            work.report.count("releases_skipped")
            continue
        if code in seen:
            # Two releases share a code in the workbook: the later one gets the next free number
            # of that year, and is found again by its EurekAlert link (BRIEF step 1.8).
            ea_url = read_text(row.cells["ea_url"]).value
            again = next(
                (
                    release
                    for release in existing
                    if ea_url and release.ea_url == ea_url and release.code not in codes_in_workbook
                ),
                None,
            )
            year = _year_of(code)
            if again is not None:
                new_code = again.code
            elif year is not None:
                number = max(taken.get(year, set()), default=0) + 1
                taken.setdefault(year, set()).add(number)
                new_code = format_code(pattern, year, number)
            else:
                work.report.add("check", "skipped_no_code", row=row.number, code=code)
                work.report.count("releases_skipped")
                continue
            work.report.add(
                "check",
                "code_duplicate",
                row=row.number,
                code=code,
                column=row.headings["code"],
                value=code,
                first=seen[code],
                new=new_code,
            )
            target = again
            code = new_code
        else:
            seen[code] = row.number
            target = by_code.get(code)
            if target is not None and target.id not in imported:
                work.report.add("check", "release_made_in_app", row=row.number, code=code)
        release = await work.release_row(row, code, target)
        if release is not None:
            by_code[code] = release
            if release not in existing:
                existing.append(release)

    await work.readings()
    await db.flush()
    return work.report
