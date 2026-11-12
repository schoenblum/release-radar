"""What Analysis reads from researcher feedback (R11.4, phase-2 brief §3.2).

- *satisfaction*: the mean of the three agreement statements (1–5);
- *research outcomes*: the number of activities ticked;
- *inquiries*: the number of inquiry groups ticked, and *inquiries from outside* the
  institution (media, external researchers and students, companies, the public; D29).

Several responses to one release: the mean for satisfaction, the union for the counts. "None"
counts as 0; a skipped question is *missing*; a release without a response is *missing* (None).
"""

import uuid
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from statistics import fmean

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.release import Release
from app.models.survey import SurveyItem, SurveyResponse
from app.services.feedback.template import ACTIVITIES, INQUIRIES, SATISFACTION


@dataclass(frozen=True)
class FeedbackDimensions:
    responses: int
    satisfaction: float | None
    research_outcomes: int | None
    inquiries: int | None
    inquiries_external: int | None
    # Which groups and activities were ticked, for the Overview's bar charts (Daniel,
    # 2026-11-12). None: the question was not answered.
    inquiry_keys: frozenset[str] | None = None
    activity_keys: frozenset[str] | None = None


@dataclass(frozen=True)
class ItemInfo:
    question: str
    exclusive: bool
    external: bool


def _ticked(answers: dict, items: dict[str, ItemInfo], question: str) -> set[str] | None:
    keys = [key for key, item in items.items() if item.question == question]
    if not any(key in answers for key in keys):
        return None
    return {key for key in keys if answers.get(key) is True and not items[key].exclusive}


def dimensions(
    answer_sets: Iterable[dict], items: dict[str, ItemInfo]
) -> FeedbackDimensions | None:
    """One release's dimensions from its responses' answers. None without any response."""
    answer_sets = list(answer_sets)
    if not answer_sets:
        return None
    scores: list[float] = []
    outcomes: set[str] | None = None
    inquiries: set[str] | None = None
    statements = [key for key, item in items.items() if item.question == SATISFACTION]
    for answers in answer_sets:
        given = [answers[key] for key in statements if isinstance(answers.get(key), int)]
        if given:
            scores.append(fmean(given))
        for question in (ACTIVITIES, INQUIRIES):
            ticked = _ticked(answers, items, question)
            if ticked is None:
                continue
            if question == ACTIVITIES:
                outcomes = (outcomes or set()) | ticked
            else:
                inquiries = (inquiries or set()) | ticked
    return FeedbackDimensions(
        responses=len(answer_sets),
        satisfaction=fmean(scores) if scores else None,
        research_outcomes=len(outcomes) if outcomes is not None else None,
        inquiries=len(inquiries) if inquiries is not None else None,
        inquiries_external=(
            sum(1 for key in inquiries if items[key].external) if inquiries is not None else None
        ),
        inquiry_keys=frozenset(inquiries) if inquiries is not None else None,
        activity_keys=frozenset(outcomes) if outcomes is not None else None,
    )


async def by_release(
    db: AsyncSession, institution_id: uuid.UUID
) -> dict[uuid.UUID, FeedbackDimensions]:
    """Every release with feedback, with its dimensions. Releases without are absent: missing."""
    items: dict[uuid.UUID, dict[str, ItemInfo]] = defaultdict(dict)
    for item in await db.scalars(
        select(SurveyItem).where(SurveyItem.institution_id == institution_id)
    ):
        items[item.template_id][item.key] = ItemInfo(item.question, item.exclusive, item.external)
    grouped: dict[uuid.UUID, list[tuple[uuid.UUID, dict]]] = defaultdict(list)
    rows = await db.execute(
        select(SurveyResponse.release_id, SurveyResponse.template_id, SurveyResponse.answers)
        .join(Release, Release.id == SurveyResponse.release_id)
        .where(SurveyResponse.institution_id == institution_id, Release.deleted_at.is_(None))
    )
    for release_id, template_id, answers in rows.all():
        grouped[release_id].append((template_id, answers))
    result: dict[uuid.UUID, FeedbackDimensions] = {}
    for release_id, responses in grouped.items():
        # Item keys are stable across versions (R11.1), so one release's responses combine.
        known: dict[str, ItemInfo] = {}
        for template_id, _ in responses:
            known.update(items[template_id])
        found = dimensions((answers for _, answers in responses), known)
        if found is not None:
            result[release_id] = found
    return result
