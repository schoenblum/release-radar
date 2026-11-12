"""Value states of readings, and the applicability rules that set them (BRIEF section 6.5).

Stored states: ``value``, ``not_applicable``, ``missing``. ``not_yet_due`` is computed.

Rules run on every save of a release, so they apply however the release was changed.
What a rule may do is deliberately narrow, so automation never overrides a person (P4, P5):

- A number a person entered is never touched. If someone recorded a value and the rule now
  says the measure does not apply, the value stays and the person can clear it.
- A rule moves a reading only between ``missing`` and a ``not_applicable`` that a rule set.
- A ``not_applicable`` set by a person stays until a person changes it.
- A number a job fetched (``source = auto``) belongs to the inputs it was fetched for: when
  the page or the release date changes, it is cleared, so the next run fetches it again
  (R8.1.1).
- An inferred 0 (R8.1.3, D27) is a rule's: it appears on a missing day-0 Altmetric reading when
  the paper was published on or after the release date, and goes again when that stops being
  true. A number or N/A a person enters replaces it; clearing theirs lets it return.
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
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
_RULE_INPUTS = ("doi", "ea_url", "embargoed", "publication_date", "release_date", "website_url")
# Measures whose missing reading is 0 when it cannot be anything else (R8.1.3, D27).
INFERRED_ZERO = frozenset({"altmetric.d0"})
# Sources whose numbers a job fetches, and the release fields such a number was fetched for.
FETCHED_SOURCES = frozenset({"ga4"})
_FETCH_INPUTS = frozenset({"website_url", "release_date"})


def _present(text: str | None) -> bool:
    return bool(text and text.strip())


def _host(url: str) -> str:
    url = url.strip()
    try:
        return (urlsplit(url if "//" in url else f"//{url}").hostname or "").lower()
    except ValueError:
        return ""


def url_on_domain(url: str | None, domain: str | None) -> bool:
    # Exact host: a parent domain or a sibling such as an older site does not count (D23).
    if not _present(url) or not _present(domain):
        return False
    return _host(url) == domain.strip().lower()


def on_domain(release: Release, domain: str | None) -> bool:
    return url_on_domain(release.website_url, domain)


def measure_applies(measure: Measure, release: Release, website_domain: str | None) -> bool:
    """Whether this measure can exist for this release (R6.5.1, R6.7.1)."""
    # A calculated count (pickups) is collected from a date on; without that date it is not
    # applicable to anything, or the default profile would score nothing (R8.1.4, R10.10).
    if measure.source == "derived" and measure.collected_from is None:
        return False
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
        return on_domain(release, website_domain)
    return True


def zero_is_inferred(measure: Measure, release: Release) -> bool:
    """A paper published on or after the release day had no attention before it (D27)."""
    return (
        measure.key in INFERRED_ZERO
        and release.release_date is not None
        and release.publication_date is not None
        and release.publication_date >= release.release_date
    )


def settle_inference(reading: Reading, measure: Measure, release: Release, applies: bool) -> bool:
    """Put an inferred 0 where the rule says, and take it away where it no longer does.

    Only ever between ``missing`` and an inferred 0: a person's number or N/A is left alone.
    True if the reading changed; the caller raises its version.
    """
    infer = applies and zero_is_inferred(measure, release)
    if reading.inferred:
        if infer:
            return False
        reading.value = None
        reading.inferred = False
        reading.state = STATE_MISSING if applies else STATE_NOT_APPLICABLE
        reading.source = SOURCE_AUTO
        return True
    if infer and reading.state == STATE_MISSING:
        reading.value = Decimal(0)
        reading.state = STATE_VALUE
        reading.source = SOURCE_AUTO
        reading.inferred = True
        return True
    return False


def _next_state(reading: Reading, applies: bool) -> str | None:
    """The state a rule moves this reading to, or None to leave it."""
    if applies and reading.state == STATE_NOT_APPLICABLE and reading.source == SOURCE_AUTO:
        return STATE_MISSING
    if not applies and reading.state == STATE_MISSING:
        return STATE_NOT_APPLICABLE
    return None


def _apply_rules(
    session: Session, release: Release, is_new: bool, changed: frozenset[str] = frozenset()
) -> None:
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
            reading = Reading(
                id=uuid.uuid4(),
                institution_id=release.institution_id,
                release=release,
                measure=measure,
                state=STATE_MISSING if applies else STATE_NOT_APPLICABLE,
                source=SOURCE_AUTO,
                inferred=False,
            )
            settle_inference(reading, measure, release, applies)
            session.add(reading)
            continue
        moved = False
        if (
            changed & _FETCH_INPUTS
            and measure.source in FETCHED_SOURCES
            and reading.state == STATE_VALUE
            and reading.source == SOURCE_AUTO
            and not reading.inferred
        ):
            # Fetched for another page or other days: let the next run fetch it again.
            reading.value = None
            reading.state = STATE_MISSING if applies else STATE_NOT_APPLICABLE
            moved = True
        else:
            next_state = _next_state(reading, applies)
            if next_state is not None:
                reading.state = next_state
                reading.source = SOURCE_AUTO
                moved = True
        if settle_inference(reading, measure, release, applies) or moved:
            reading.version += 1


def apply_rules_to_changed_releases(session: Session) -> None:
    """Called before every flush. Creates readings and moves their states."""
    new = [obj for obj in session.new if isinstance(obj, Release)]
    changed: list[tuple[Release, frozenset[str]]] = []
    for obj in session.dirty:
        if not isinstance(obj, Release):
            continue
        attrs = inspect(obj).attrs
        inputs = frozenset(name for name in _RULE_INPUTS if attrs[name].history.has_changes())
        if inputs:
            changed.append((obj, inputs))
    if not new and not changed:
        return
    with session.no_autoflush:
        for release in new:
            _apply_rules(session, release, is_new=True)
        for release, inputs in changed:
            _apply_rules(session, release, is_new=False, changed=inputs)


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


def reminder_date(due: date | None, remind_days_before: int) -> date | None:
    """The day a reminder goes out: the due day itself, or the day before (R6.5.3)."""
    return None if due is None else due - timedelta(days=remind_days_before)


def today_in(timezone_name: str, now: datetime | None = None) -> date:
    """Today's date at the institution, which is not the date in UTC for part of each day."""
    return (now or datetime.now(UTC)).astimezone(ZoneInfo(timezone_name)).date()


def display_state(state: str, due: date | None, today: date) -> str:
    """The state to show. ``missing`` before its date means ``not_yet_due`` (R6.5.1)."""
    if state == STATE_MISSING and (due is None or due > today):
        return STATE_NOT_YET_DUE
    return state
