"""Value states of readings, and the applicability rules that set them (BRIEF section 6.5).

Stored states: ``value``, ``not_applicable``, ``missing``. ``not_yet_due`` is computed.

Rules run on every save of a release, so they apply however the release was changed.
What a rule may do is deliberately narrow, so automation never overrides a person (P4, P5):

- A number is never touched. If someone recorded a value and the rule now says the measure
  does not apply, the value stays and the person can clear it.
- A rule moves a reading only between ``missing`` and a ``not_applicable`` that a rule set.
- A ``not_applicable`` set by a person stays until a person changes it.
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.models.institution import Institution
from app.models.release import Measure, Reading, Release

STATE_VALUE = "value"
STATE_NOT_APPLICABLE = "not_applicable"
STATE_MISSING = "missing"
STATE_NOT_YET_DUE = "not_yet_due"
SOURCE_AUTO = "auto"
SOURCE_MANUAL = "manual"

# The release fields that any rule depends on. Saving anything else skips the rules.
_RULE_INPUTS = ("doi", "ea_url", "embargoed", "release_date", "website_url")


def _present(text: str | None) -> bool:
    return bool(text and text.strip())


def _host(url: str) -> str:
    url = url.strip()
    try:
        return (urlsplit(url if "//" in url else f"//{url}").hostname or "").lower()
    except ValueError:
        return ""


def _on_domain(release: Release, domain: str | None) -> bool:
    # Exact host: a parent domain or a sibling such as an older site does not count (D23).
    if not _present(release.website_url) or not _present(domain):
        return False
    return _host(release.website_url) == domain.strip().lower()


def measure_applies(measure: Measure, release: Release, website_domain: str | None) -> bool:
    """Whether this measure can exist for this release (R6.5.1, R6.7.1)."""
    if (
        measure.collected_from is not None
        and release.release_date is not None
        and release.release_date < measure.collected_from
    ):
        return False
    rule = measure.applicability
    if rule == "embargoed":
        return bool(release.embargoed)
    if rule == "has_doi":
        return _present(release.doi)
    if rule == "has_ea_url":
        return _present(release.ea_url)
    if rule == "website_on_domain":
        return _on_domain(release, website_domain)
    return True


def _next_state(reading: Reading, applies: bool) -> str | None:
    """The state a rule moves this reading to, or None to leave it."""
    if applies and reading.state == STATE_NOT_APPLICABLE and reading.source == SOURCE_AUTO:
        return STATE_MISSING
    if not applies and reading.state == STATE_MISSING:
        return STATE_NOT_APPLICABLE
    return None


def _apply_rules(session: Session, release: Release, is_new: bool) -> None:
    # The default ID is otherwise assigned only at insert, and readings need it now.
    if release.id is None:
        release.id = uuid.uuid4()
    institution = session.get(Institution, release.institution_id)
    domain = institution.website_domain if institution else None
    measures = session.scalars(
        select(Measure).where(
            Measure.institution_id == release.institution_id, Measure.is_active.is_(True)
        )
    ).all()
    existing = (
        {}
        if is_new
        else {
            reading.measure_id: reading
            for reading in session.scalars(select(Reading).where(Reading.release_id == release.id))
        }
    )
    for measure in measures:
        applies = measure_applies(measure, release, domain)
        reading = existing.get(measure.id)
        if reading is None:
            session.add(
                Reading(
                    id=uuid.uuid4(),
                    institution_id=release.institution_id,
                    release=release,
                    measure=measure,
                    state=STATE_MISSING if applies else STATE_NOT_APPLICABLE,
                    source=SOURCE_AUTO,
                )
            )
            continue
        next_state = _next_state(reading, applies)
        if next_state is not None:
            reading.state = next_state
            reading.source = SOURCE_AUTO
            reading.version += 1


def apply_rules_to_changed_releases(session: Session) -> None:
    """Called before every flush. Creates readings and moves their states."""
    new = [obj for obj in session.new if isinstance(obj, Release)]
    changed = [
        obj
        for obj in session.dirty
        if isinstance(obj, Release)
        and any(inspect(obj).attrs[name].history.has_changes() for name in _RULE_INPUTS)
    ]
    if not new and not changed:
        return
    with session.no_autoflush:
        for release in new:
            _apply_rules(session, release, is_new=True)
        for release in changed:
            _apply_rules(session, release, is_new=False)


def resync_institution(session: Session, institution_id: uuid.UUID) -> None:
    """Re-run the rules for every release, after something the rules read has changed."""
    releases = session.scalars(select(Release).where(Release.institution_id == institution_id))
    with session.no_autoflush:
        for release in releases.all():
            _apply_rules(session, release, is_new=False)


def due_date(release_date: date | None, offset_days: int | None) -> date | None:
    """When a reading falls due. None without a release date (R7.5.6) or a checkpoint."""
    if release_date is None or offset_days is None:
        return None
    return release_date + timedelta(days=offset_days)


def today_in(timezone_name: str, now: datetime | None = None) -> date:
    """Today's date at the institution, which is not the date in UTC for part of each day."""
    return (now or datetime.now(UTC)).astimezone(ZoneInfo(timezone_name)).date()


def display_state(state: str, due: date | None, today: date) -> str:
    """The state to show. ``missing`` before its date means ``not_yet_due`` (R6.5.1)."""
    if state == STATE_MISSING and (due is None or due > today):
        return STATE_NOT_YET_DUE
    return state
