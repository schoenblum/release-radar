"""The Analysis area (phase-2 brief §5, BRIEF §8.4): overview, a page per dimension, top and
bottom 5, their exports, and the Data page's positions. Every signed-in role reads it (D16);
nothing here is reachable without a session. The writer is never a filter, column or grouping
(D9).

Both filters come in the query string as the pages keep them in the address: ``a_<dim>`` for
*analysed*, ``s_<dim>`` for *shown*, each a comma-separated list, ``all`` for every value, and
absent for the institution's default. Values that cannot be read are ignored, so an old bookmark
still opens. *Shown* always lies within *analysed*.
"""

import asyncio
import uuid
from collections import Counter
from collections.abc import Callable
from datetime import datetime
from typing import Any, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.i18n import t
from app.models import (
    Institution,
    ReleaseType,
    ResearchField,
    ScoreProfile,
    ScoreProfileVersion,
    Unit,
    User,
)
from app.schemas.analysis import (
    BoxOut,
    CardOut,
    CountsOut,
    DimensionOut,
    EntryOut,
    FilterOut,
    OptionOut,
    OptionsOut,
    OverviewOut,
    PageOut,
    PointOut,
    PositionsOut,
    ProfileRef,
    ScopeOut,
    TopOut,
)
from app.services import release_export
from app.services.analysis import dataset as analysis
from app.services.analysis.filters import GENDERS, AnalysisFilter
from app.services.analysis.pages import (
    SCORE,
    Analysis,
    Card,
    Entry,
    basis_or_default,
    page_keys,
)
from app.services.analysis.profiles import default_filters, spec_of
from app.services.analysis.scoring import ALTMETRIC, BASIS_INCREASE
from app.services.readings import today_in
from app.services.release_export import Table

router = APIRouter(prefix="/analysis", tags=["analysis"])

# The filter dimensions as the address names them, and the AnalysisFilter field behind each.
DIMENSIONS = {
    "type": "release_types",
    "ay": "academic_years",
    "unit": "units",
    "field": "fields",
    "emb": "embargoed",
    "gender": "genders",
}
_LISTED = ("type", "unit", "field")
_MEDIA_TYPES = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "csv": "text/csv; charset=utf-8",
}
_MAX_TOKENS = 500


def _token(dimension: str, text: str) -> Any:
    """One value from the address, or ``...`` when it cannot be read."""
    if dimension in _LISTED:
        if text == "none":
            return None
        try:
            return uuid.UUID(text)
        except ValueError:
            return ...
    if dimension == "ay":
        return int(text) if text.isdigit() and 1900 <= int(text) <= 2999 else ...
    if dimension == "emb":
        return {"1": True, "0": False}.get(text, ...)
    return text if text in GENDERS else ...


def _parse(params: Any, prefix: str, default: AnalysisFilter) -> AnalysisFilter:
    values: dict[str, Any] = {}
    for dimension, name in DIMENSIONS.items():
        raw = params.get(f"{prefix}_{dimension}")
        if raw is None:
            values[name] = getattr(default, name)
            continue
        raw = raw.strip()
        if raw == "all":
            values[name] = None
            continue
        tokens = [_token(dimension, part.strip()) for part in raw.split(",")[:_MAX_TOKENS]]
        found = frozenset(token for token in tokens if token is not ...)
        values[name] = found if found else getattr(default, name)
    return AnalysisFilter(**values)


def _within(shown: AnalysisFilter, analysed: AnalysisFilter) -> AnalysisFilter:
    """Shown never reaches outside analysed. Nothing in common: everything analysed is shown."""
    values: dict[str, Any] = {}
    for name in DIMENSIONS.values():
        outer, inner = getattr(analysed, name), getattr(shown, name)
        if outer is None or inner is None:
            values[name] = inner
        else:
            values[name] = (inner & outer) or None
    return AnalysisFilter(**values)


def filters_from(params: Any, institution: Institution) -> tuple[AnalysisFilter, AnalysisFilter]:
    default_analysed, default_shown = default_filters(institution)
    analysed = _parse(params, "a", default_analysed)
    shown = _within(_parse(params, "s", default_shown), analysed)
    return analysed, shown


def _filter_out(found: AnalysisFilter) -> FilterOut:
    def text(value: Any) -> str:
        if value is None:
            return "none"
        if isinstance(value, bool):
            return "1" if value else "0"
        return str(value)

    return FilterOut(
        **{
            dimension: None
            if getattr(found, name) is None
            else sorted(text(value) for value in getattr(found, name))
            for dimension, name in DIMENSIONS.items()
        }
    )


async def _profile(
    db: AsyncSession, institution_id: uuid.UUID, profile_id: uuid.UUID | None
) -> tuple[ScoreProfile, ScoreProfileVersion] | None:
    """The asked profile's current version, or the default's."""
    query = (
        select(ScoreProfile, ScoreProfileVersion)
        .join(ScoreProfileVersion, ScoreProfileVersion.profile_id == ScoreProfile.id)
        .where(ScoreProfile.institution_id == institution_id)
        .order_by(ScoreProfileVersion.version.desc())
        .limit(1)
    )
    if profile_id is not None:
        query = query.where(ScoreProfile.id == profile_id)
    else:
        query = query.where(ScoreProfile.is_default.is_(True))
    found = (await db.execute(query)).first()
    if found is None and profile_id is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
    return (found[0], found[1]) if found else None


def _profile_ref(profile: ScoreProfile, version: ScoreProfileVersion) -> ProfileRef:
    return ProfileRef(
        id=profile.id,
        version=version.version,
        name_en=version.name_en,
        name_ja=version.name_ja,
        is_default=profile.is_default,
        altmetric_basis=version.altmetric_basis,
        coverage_min=version.coverage_min,
        comparison_years=version.comparison_years,
        min_values=version.min_values,
    )


class Context:
    """One request: the institution, both filters, the profile and the computed analysis."""

    def __init__(
        self,
        institution: Institution,
        analysis_: Analysis,
        profile: ProfileRef | None,
    ) -> None:
        self.institution = institution
        self.analysis = analysis_
        self.profile = profile

    def scope(self) -> ScopeOut:
        found = self.analysis
        analysed = found.analysed_rows
        years = [row.academic_year for row in analysed]
        return ScopeOut(
            analysed=_filter_out(found.analysed),
            shown=_filter_out(found.shown),
            analysed_count=len(analysed),
            shown_count=len(found.shown_rows),
            first_year=min(years) if years else None,
            last_year=max(years) if years else None,
            profile=self.profile,
            altmetric_basis=found.altmetric_basis,
            today=found.dataset.today,
        )


async def _context(
    request: Request,
    user: User,
    db: AsyncSession,
    profile_id: uuid.UUID | None,
    altmetric: str | None,
) -> Context:
    institution = await db.get(Institution, user.institution_id)
    analysed, shown = filters_from(request.query_params, institution)
    chosen = await _profile(db, institution.id, profile_id)
    spec = spec_of(chosen[1]) if chosen else None
    dataset = await analysis.load(db, institution, today_in(institution.timezone))
    found = Analysis(
        dataset=dataset,
        analysed=analysed,
        shown=shown,
        spec=spec,
        altmetric_basis=basis_or_default(altmetric, spec),
    )
    return Context(institution, found, _profile_ref(*chosen) if chosen else None)


def _card_out(card: Card) -> CardOut:
    box = card.box
    return CardOut(
        key=card.key,
        dimension=card.dimension,
        label_en=card.label_en,
        label_ja=card.label_ja,
        unit=card.unit,
        decimals=card.decimals,
        box=BoxOut(low=box.low, q1=box.q1, median=box.median, q3=box.q3, high=box.high, n=box.n)
        if box
        else None,
        counts=CountsOut(**vars(card.counts)),
        points=[
            PointOut(
                id=entry.row.id,
                code=entry.row.code,
                title=entry.row.title,
                value=entry.value,
                inferred=entry.inferred,
            )
            for entry in card.points
        ],
        shown_median=card.shown_median,
    )


def _entry_out(entry: Entry) -> EntryOut:
    row = entry.row
    return EntryOut(
        id=row.id,
        code=row.code,
        title=row.title,
        release_date=row.release_date,
        academic_year=row.academic_year,
        unit_id=row.unit_id,
        field_id=row.field_id,
        value=entry.value,
        state=entry.state,
        inferred=entry.inferred,
        provisional=entry.provisional,
        rank=entry.rank,
        percentile=entry.percentile,
        coverage=entry.coverage,
        components=entry.components,
    )


def _page_key(context: Context, key: str) -> str:
    keys = page_keys(context.analysis.dataset)
    if key not in keys or (key == SCORE and context.profile is None):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
    return key


# ---------------------------------------------------------------- options


async def _named(db: AsyncSession, model: Any, institution_id: uuid.UUID) -> dict[uuid.UUID, Any]:
    return {
        item.id: item
        for item in await db.scalars(select(model).where(model.institution_id == institution_id))
    }


@router.get("/options", response_model=OptionsOut)
async def options(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> OptionsOut:
    """The values each filter can take, among dated releases, with how many releases have each."""
    institution = await db.get(Institution, user.institution_id)
    dataset = await analysis.load(db, institution, today_in(institution.timezone))
    rows = dataset.rows
    types = await _named(db, ReleaseType, institution.id)
    units = await _named(db, Unit, institution.id)
    research_fields = await _named(db, ResearchField, institution.id)

    def listed(counter: Counter, items: dict[uuid.UUID, Any], ordered: bool) -> list[OptionOut]:
        found: list[OptionOut] = []
        for value, count in counter.items():
            item = items.get(value)
            found.append(
                OptionOut(
                    value=str(value) if value is not None else "none",
                    label_en=item.name_en if item else None,
                    label_ja=item.name_ja if item else None,
                    short_en=getattr(item, "short_label", None) if item else None,
                    count=count,
                )
            )

        def order(option: OptionOut) -> tuple:
            item = items.get(uuid.UUID(option.value)) if option.value != "none" else None
            if item is None:
                return (1, 0, "")
            return (0, getattr(item, "position", 0) if ordered else 0, item.name_en.lower())

        return sorted(found, key=order)

    profiles = (
        await db.execute(
            select(ScoreProfile, ScoreProfileVersion)
            .join(ScoreProfileVersion, ScoreProfileVersion.profile_id == ScoreProfile.id)
            .where(ScoreProfile.institution_id == institution.id)
            .order_by(
                ScoreProfile.is_default.desc(),
                ScoreProfile.created_at,
                ScoreProfileVersion.version.desc(),
            )
        )
    ).all()
    current: dict[uuid.UUID, ProfileRef] = {}
    for profile, version in profiles:
        current.setdefault(profile.id, _profile_ref(profile, version))

    pages: list[PageOut] = []
    probe = Analysis(dataset, AnalysisFilter(), AnalysisFilter(), None, BASIS_INCREASE)
    for key in page_keys(dataset):
        if key == SCORE and not current:
            continue
        described = probe.describe(key)
        pages.append(PageOut(key=key, label_en=described.label_en, label_ja=described.label_ja))

    return OptionsOut(
        release_types=listed(Counter(row.release_type_id for row in rows), types, True),
        academic_years=[
            OptionOut(value=str(year), count=count)
            for year, count in sorted(
                Counter(row.academic_year for row in rows).items(), reverse=True
            )
        ],
        units=listed(Counter(row.unit_id for row in rows), units, False),
        fields=listed(Counter(row.field_id for row in rows), research_fields, False),
        embargoed=[
            OptionOut(value=value, count=count)
            for value, count in (
                ("1", sum(1 for row in rows if row.embargoed)),
                ("0", sum(1 for row in rows if not row.embargoed)),
            )
            if count
        ],
        genders=[
            OptionOut(value=gender, count=count)
            for gender in GENDERS
            if (count := sum(1 for row in rows if row.gender == gender))
        ],
        pages=pages,
        profiles=list(current.values()),
    )


# ---------------------------------------------------------------- pages


@router.get("/overview", response_model=OverviewOut)
async def overview(
    request: Request,
    profile: uuid.UUID | None = None,
    altmetric: Literal["increase", "d28"] | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OverviewOut:
    """One card per dimension with data, the score first (phase-2 brief §5.2)."""
    context = await _context(request, user, db, profile, altmetric)
    keys = [
        key
        for key in page_keys(context.analysis.dataset)
        if key != SCORE or context.profile is not None
    ]
    return OverviewOut(
        scope=context.scope(),
        cards=[_card_out(context.analysis.card(key)) for key in keys],
    )


@router.get("/dimensions/{key}", response_model=DimensionOut)
async def dimension_page(
    key: str,
    request: Request,
    profile: uuid.UUID | None = None,
    altmetric: Literal["increase", "d28"] | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DimensionOut:
    """The card's numbers and the ranked list of shown releases (phase-2 brief §5.3)."""
    context = await _context(request, user, db, profile, altmetric)
    key = _page_key(context, key)
    return DimensionOut(
        scope=context.scope(),
        card=_card_out(context.analysis.card(key)),
        rows=[_entry_out(entry) for entry in context.analysis.rows(key)],
    )


@router.get("/top", response_model=TopOut)
async def top_and_bottom(
    request: Request,
    dimension: str = SCORE,
    profile: uuid.UUID | None = None,
    altmetric: Literal["increase", "d28"] | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TopOut:
    """The five highest and lowest finished, shown releases (phase-2 brief §5.4)."""
    context = await _context(request, user, db, profile, altmetric)
    key = _page_key(context, dimension)
    described = context.analysis.describe(key)
    highest, lowest = context.analysis.top_and_bottom(key)
    return TopOut(
        scope=context.scope(),
        key=key,
        label_en=described.label_en,
        label_ja=described.label_ja,
        unit=described.unit,
        decimals=described.decimals,
        highest=[_entry_out(entry) for entry in highest],
        lowest=[_entry_out(entry) for entry in lowest],
    )


@router.get("/positions", response_model=PositionsOut)
async def positions(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> PositionsOut:
    """Every measure's percentile per release, from the default profile's settings and the
    default inclusion filter (phase-2 brief §5.5). Releases outside that set are left out."""
    institution = await db.get(Institution, user.institution_id)
    analysed, shown = default_filters(institution)
    chosen = await _profile(db, institution.id, None)
    spec = spec_of(chosen[1]) if chosen else None
    dataset = await analysis.load(db, institution, today_in(institution.timezone))
    found = Analysis(dataset, analysed, shown, spec, basis_or_default(None, spec))
    measures = [item.key for item in dataset.dimensions if item.kind == "measure"]
    return PositionsOut(measures=measures, releases=found.positions(measures))


# ---------------------------------------------------------------- exports


def _round(value: float | None, decimals: int) -> int | float | None:
    if value is None:
        return None
    rounded = round(value, decimals)
    return int(rounded) if decimals == 0 else rounded


async def _labels(db: AsyncSession, institution_id: uuid.UUID, language: str) -> Callable:
    types = await _named(db, ReleaseType, institution_id)
    units = await _named(db, Unit, institution_id)
    research_fields = await _named(db, ResearchField, institution_id)

    def name(items: dict, value: uuid.UUID | None) -> str | None:
        item = items.get(value)
        if item is None:
            return None
        return (language == "ja" and item.name_ja) or item.name_en

    def label(dimension: str, value: Any) -> str:
        if dimension in _LISTED and value is None:
            return t(language, f"analysis_export.none.{dimension}")
        if dimension == "type":
            return name(types, value) or str(value)
        if dimension == "unit":
            return name(units, value) or str(value)
        if dimension == "field":
            return name(research_fields, value) or str(value)
        if dimension == "ay":
            return t(language, "export.readme.academic_year", year=value)
        if dimension == "emb":
            return t(
                language,
                "analysis_export.embargoed_yes" if value else "analysis_export.embargoed_no",
            )
        return t(language, f"export.genders.{value}")

    return label


def _describe(found: AnalysisFilter, label: Callable, language: str) -> str:
    parts: list[str] = []
    for dimension, name in DIMENSIONS.items():
        allowed = getattr(found, name)
        if allowed is None:
            continue
        values = sorted(label(dimension, value) for value in allowed)
        parts.append(
            t(
                language,
                "analysis_export.restriction",
                dimension=t(language, f"analysis_export.dimensions.{dimension}"),
                values=t(language, "export.readme.separator").join(values),
            )
        )
    if not parts:
        return t(language, "analysis_export.everything")
    return t(language, "analysis_export.joiner").join(parts)


def _state(entry: Entry, language: str) -> str:
    return t(language, f"analysis_export.states.{entry.state}")


async def _table(
    db: AsyncSession, context: Context, key: str, entries: list[Entry], language: str
) -> Table:
    found = context.analysis
    described = found.describe(key)
    is_score = key == SCORE
    units = await _named(db, Unit, context.institution.id)
    research_fields = await _named(db, ResearchField, context.institution.id)

    def name(items: dict, value: uuid.UUID | None) -> str | None:
        item = items.get(value)
        if item is None:
            return None
        return (language == "ja" and item.name_ja) or item.name_en

    label = described.label_ja if language == "ja" else described.label_en
    headers = [
        t(language, "analysis_export.columns.rank"),
        t(language, "export.fields.code"),
        t(language, "export.fields.title"),
        t(language, "export.fields.release_date"),
        t(language, "export.fields.academic_year"),
        t(language, "export.fields.unit"),
        t(language, "export.fields.field"),
        label,
    ]
    if is_score:
        headers += [
            t(language, "analysis_export.columns.coverage"),
            t(language, "analysis_export.columns.based_on"),
        ]
    else:
        headers += [
            t(language, "analysis_export.columns.percentile"),
            t(language, "export.inferred_column", label=label),
        ]
    headers += [
        t(language, "analysis_export.columns.state"),
        t(language, "analysis_export.columns.provisional"),
    ]
    components = {
        item.key: item.label_ja if language == "ja" else item.label_en
        for item in found.dataset.dimensions
    }
    components[ALTMETRIC] = t(language, "analysis.dimensions.altmetric")
    table = Table(headers=headers)
    for entry in entries:
        row = entry.row
        cells: list[Any] = [
            entry.rank,
            row.code,
            row.title,
            row.release_date,
            row.academic_year,
            name(units, row.unit_id),
            name(research_fields, row.field_id),
            _round(entry.value, described.decimals),
        ]
        if is_score:
            cells += [
                _round(entry.coverage * 100, 0) if entry.coverage is not None else None,
                t(language, "export.readme.separator").join(
                    components.get(item, item) for item in entry.components
                )
                or None,
            ]
        else:
            cells += [_round(entry.percentile, 1), 1 if entry.inferred else 0]
        cells += [_state(entry, language), 1 if entry.provisional else 0]
        table.rows.append(cells)
    return table


async def _read_me(
    db: AsyncSession,
    context: Context,
    key: str,
    language: str,
    who: str,
    when: datetime,
    *,
    top: bool,
) -> list[str]:
    found = context.analysis
    described = found.describe(key)
    label = await _labels(db, context.institution.id, language)
    scope = context.scope()
    name = described.label_ja if language == "ja" else described.label_en
    lines = [
        t(
            language,
            "analysis_export.readme.title_top" if top else "analysis_export.readme.title",
            name=name,
        ),
        t(language, "export.readme.exported", when=when.strftime("%Y-%m-%d %H:%M"), who=who),
        "",
        t(
            language,
            "analysis_export.readme.analysed",
            count=scope.analysed_count,
            filters=_describe(found.analysed, label, language),
        ),
        t(
            language,
            "analysis_export.readme.shown",
            count=scope.shown_count,
            filters=_describe(found.shown, label, language),
        ),
    ]
    if context.profile is not None:
        profile = context.profile
        lines.append(
            t(
                language,
                "analysis_export.readme.profile",
                name=(language == "ja" and profile.name_ja) or profile.name_en,
                version=profile.version,
                years=profile.comparison_years,
                minimum=profile.min_values,
                coverage=profile.coverage_min,
            )
        )
    if key == ALTMETRIC:
        lines.append(t(language, f"analysis_export.readme.altmetric_{found.altmetric_basis}"))
    lines += [
        "",
        t(language, "analysis_export.readme.top" if top else "analysis_export.readme.rows"),
        t(language, "analysis_export.readme.rank"),
    ]
    if key == SCORE:
        lines.append(t(language, "analysis_export.readme.score"))
    else:
        lines.append(t(language, "analysis_export.readme.percentile"))
    lines += [
        t(language, "analysis_export.readme.provisional"),
        t(language, "analysis_export.readme.quartiles"),
        "",
        t(language, "export.readme.personal"),
    ]
    return lines


async def _file(
    db: AsyncSession,
    context: Context,
    user: User,
    key: str,
    sheets: list[tuple[str, Table]],
    file_format: str,
    language: str,
    *,
    top: bool,
) -> Response:
    now = datetime.now(ZoneInfo(context.institution.timezone))
    if file_format == "csv":
        if len(sheets) == 1:
            table = sheets[0][1]
        else:
            # One file for both lists: a column says which list a row belongs to.
            first = sheets[0][1]
            table = Table(headers=[t(language, "analysis_export.columns.list"), *first.headers])
            for name, part in sheets:
                table.rows += [[name, *row] for row in part.rows]
        content = release_export.to_csv(table)
    else:
        readme = await _read_me(
            db, context, key, language, user.full_name or user.email, now, top=top
        )
        content = await asyncio.to_thread(
            release_export.to_xlsx,
            sheets[0],
            dict(sheets[1:]),
            (t(language, "export.sheets.readme"), readme),
        )
    kind = "top" if top else "analysis"
    safe = key.replace(".", "_")
    filename = f"release_radar_{kind}_{safe}_{now.strftime('%Y%m%d')}.{file_format}"
    return Response(
        content=content,
        media_type=_MEDIA_TYPES[file_format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/dimensions/{key}/export")
async def export_dimension(
    key: str,
    request: Request,
    profile: uuid.UUID | None = None,
    altmetric: Literal["increase", "d28"] | None = None,
    file_format: Literal["xlsx", "csv"] = Query("xlsx", alias="format"),
    language: Literal["en", "ja"] = Query("en"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """The ranked list as on the page, with a Read me naming both filters and the profile."""
    context = await _context(request, user, db, profile, altmetric)
    key = _page_key(context, key)
    table = await _table(db, context, key, context.analysis.rows(key), language)
    sheet = t(language, "analysis_export.sheets.ranking")
    return await _file(db, context, user, key, [(sheet, table)], file_format, language, top=False)


@router.get("/top/export")
async def export_top(
    request: Request,
    dimension: str = SCORE,
    profile: uuid.UUID | None = None,
    altmetric: Literal["increase", "d28"] | None = None,
    file_format: Literal["xlsx", "csv"] = Query("xlsx", alias="format"),
    language: Literal["en", "ja"] = Query("en"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    context = await _context(request, user, db, profile, altmetric)
    key = _page_key(context, dimension)
    highest, lowest = context.analysis.top_and_bottom(key)
    sheets = [
        (
            t(language, "analysis_export.sheets.highest"),
            await _table(db, context, key, highest, language),
        ),
        (
            t(language, "analysis_export.sheets.lowest"),
            await _table(db, context, key, lowest, language),
        ),
    ]
    return await _file(db, context, user, key, sheets, file_format, language, top=True)
