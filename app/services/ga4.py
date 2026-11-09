"""Website views from Google Analytics 4 (R8.1.1, phase-2 brief section 3.1).

A service account's JSON key, stored Fernet-encrypted, signs a short-lived token request
(OAuth 2.0 JWT bearer, signed here with PyJWT, so no Google library is needed), and the
Analytics Data API's ``runReport`` counts ``screenPageViews`` for one page over the 28 days
from its release date.

The job catches up rather than firing on a date: each run takes every release whose window
has closed and whose reading is still missing, so a run missed while the Mac slept costs
nothing, and the first run is the backfill. A person's number or N/A is never touched (P4).
No rows for a path leaves the reading missing, never 0. Every run leaves a status with its
counts, and "skipped" with the reason when it cannot run.
"""

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from urllib.parse import quote, unquote, urlsplit

import httpx
import jwt
from cryptography.fernet import InvalidToken
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import SessionLocal, engine
from app.models.integration import KIND_GA4, Integration
from app.models.release import Checkpoint, Measure, Reading, Release
from app.services import audit, crypto
from app.services.institution import get_institution
from app.services.readings import (
    SOURCE_AUTO,
    STATE_MISSING,
    STATE_VALUE,
    today_in,
    url_on_domain,
)
from app.services.scheduler import JobResult, lock_key

logger = logging.getLogger("release-radar.ga4")

SOURCE = "ga4"
SCOPE = "https://www.googleapis.com/auth/analytics.readonly"
METRIC = "screenPageViews"
# Google Analytics needs a day or two to process a day's data.
PROCESSING_LAG_DAYS = 2
AUDIT_NOTE = "ga4_website_views"
# Replaced in tests, so that the suite never reaches Google.
_transport: httpx.AsyncBaseTransport | None = None
_TIMEOUT = httpx.Timeout(20.0, connect=5.0)
_SERVICE_ACCOUNT = "service_account"

# Errors that would fail every release the same way, so a run stops at the first one.
FATAL = frozenset(
    {"key_unreadable", "key_rejected", "api_disabled", "no_access", "wrong_property", "quota"}
)


class Ga4Error(Exception):
    """A failure with a stable code that the frontend explains in plain words."""

    def __init__(self, code: str, detail: str | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail


# Plain words for job details, which are English like every other job's.
_REASONS = {
    "no_key": "No Google Analytics key is stored. An admin can add one in Settings → Integrations.",
    "key_unreadable": "The stored key cannot be read on this install; enter it again in "
    "Settings → Integrations.",
    "no_property": "No Google Analytics property ID is set (Settings → Integrations).",
    "no_domain": "No website domain is set (Settings → Institution), so no release has "
    "website views to fetch.",
    "waiting_for_first_fetch": "Daily fetches start after the first Fetch now in Settings → "
    "Integrations.",
    "busy": "Another fetch of website views is running.",
    "key_rejected": "Google refused the key. It may have been deleted or disabled in Google "
    "Cloud; create a new key and enter it again.",
    "api_disabled": "The Google Analytics Data API is not enabled in the key's Google Cloud "
    "project.",
    "no_access": "The service account has no access to this property, or the property ID is "
    "wrong. Add the service account as Viewer in Google Analytics.",
    "wrong_property": "Google Analytics does not accept this property ID.",
    "quota": "Google Analytics' quota for this property is used up for now; the next run "
    "tries again.",
    "unreachable": "Google could not be reached.",
    "google_error": "Google Analytics answered with an error.",
}


def reason(code: str, detail: str | None = None) -> str:
    text_ = _REASONS.get(code, _REASONS["google_error"])
    return f"{text_} ({detail})" if detail and code in {"google_error", "key_rejected"} else text_


# ---------------------------------------------------------------- the key


@dataclass(frozen=True)
class ServiceAccount:
    client_email: str
    private_key: str
    private_key_id: str | None
    project_id: str | None

    def shown(self) -> dict[str, str | None]:
        """What may be shown and stored in the clear: nothing that signs anything."""
        return {"client_email": self.client_email, "project_id": self.project_id}


def parse_key(raw: str) -> ServiceAccount:
    """The service account in a downloaded JSON key, or a ``Ga4Error`` saying what is wrong."""
    try:
        data = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise Ga4Error("key_not_json") from exc
    if not isinstance(data, dict) or data.get("type") != _SERVICE_ACCOUNT:
        raise Ga4Error("key_not_service_account")
    email, private_key = data.get("client_email"), data.get("private_key")
    if not isinstance(email, str) or "@" not in email or not isinstance(private_key, str):
        raise Ga4Error("key_incomplete")
    try:
        loaded = load_pem_private_key(private_key.encode("utf-8"), password=None)
    except (ValueError, TypeError) as exc:
        raise Ga4Error("key_bad_private_key") from exc
    if not isinstance(loaded, RSAPrivateKey):
        raise Ga4Error("key_bad_private_key")
    key_id, project = data.get("private_key_id"), data.get("project_id")
    return ServiceAccount(
        client_email=email.strip(),
        private_key=private_key,
        private_key_id=key_id if isinstance(key_id, str) else None,
        project_id=project if isinstance(project, str) else None,
    )


def stored_account(integration: Integration | None) -> ServiceAccount:
    if integration is None or integration.credential is None:
        raise Ga4Error("no_key")
    try:
        return parse_key(crypto.decrypt(integration.credential))
    except (InvalidToken, Ga4Error) as exc:
        # Most likely a key stored on another install, under another FERNET_KEY (brief §2.3).
        raise Ga4Error("key_unreadable") from exc


async def load_integration(
    db: AsyncSession, institution_id: uuid.UUID, *, for_update: bool = False
) -> Integration | None:
    query = select(Integration).where(
        Integration.institution_id == institution_id, Integration.kind == KIND_GA4
    )
    if for_update:
        query = query.with_for_update().execution_options(populate_existing=True)
    return await db.scalar(query)


def valid_property_id(value: str) -> bool:
    return value.isdigit() and 0 < len(value) <= 20


# ---------------------------------------------------------------- talking to Google


def _google_error(response: httpx.Response) -> Ga4Error:
    """Google's error answer, as one of the plain reasons."""
    try:
        error = response.json().get("error", {})
    except ValueError:
        error = {}
    if not isinstance(error, dict):
        error = {}
    status, message = error.get("status", ""), str(error.get("message", ""))[:300]
    reasons = {
        detail.get("reason")
        for detail in error.get("details", [])
        if isinstance(detail, dict) and detail.get("reason")
    }
    if "SERVICE_DISABLED" in reasons or "has not been used in project" in message:
        return Ga4Error("api_disabled")
    if response.status_code == 429 or status == "RESOURCE_EXHAUSTED":
        return Ga4Error("quota")
    if status == "PERMISSION_DENIED" or response.status_code == 403:
        return Ga4Error("no_access")
    if status in {"INVALID_ARGUMENT", "NOT_FOUND"} and "propert" in message.lower():
        return Ga4Error("wrong_property")
    if status == "UNAUTHENTICATED" or response.status_code == 401:
        return Ga4Error("key_rejected", message or None)
    return Ga4Error("google_error", message or f"HTTP {response.status_code}")


class Client:
    """One run's connection to Google Analytics, with one token for all its reports."""

    def __init__(self, account: ServiceAccount, property_id: str) -> None:
        self.account = account
        self.property_id = property_id
        self._http: httpx.AsyncClient | None = None
        self._token: str | None = None

    async def __aenter__(self) -> "Client":
        self._http = httpx.AsyncClient(transport=_transport, timeout=_TIMEOUT)
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._http is not None:
            await self._http.aclose()

    def _assertion(self) -> str:
        now = int(datetime.now(UTC).timestamp())
        claims = {
            "iss": self.account.client_email,
            "scope": SCOPE,
            "aud": get_settings().GOOGLE_TOKEN_URL,
            "iat": now,
            "exp": now + 3600,
        }
        headers = {"kid": self.account.private_key_id} if self.account.private_key_id else None
        return jwt.encode(claims, self.account.private_key, algorithm="RS256", headers=headers)

    @property
    def http(self) -> httpx.AsyncClient:
        if self._http is None:
            raise RuntimeError("Use the client in an async with block")
        return self._http

    async def _fetch_token(self) -> str:
        try:
            response = await self.http.post(
                get_settings().GOOGLE_TOKEN_URL,
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": self._assertion(),
                },
            )
        except httpx.HTTPError as exc:
            raise Ga4Error("unreachable") from exc
        if response.status_code != 200:
            try:
                body = response.json()
            except ValueError:
                body = {}
            kind = body.get("error") if isinstance(body, dict) else None
            if kind in {"invalid_grant", "invalid_client", "unauthorized_client"}:
                raise Ga4Error("key_rejected", str(body.get("error_description", ""))[:200] or None)
            raise Ga4Error("google_error", f"token HTTP {response.status_code}")
        token = response.json().get("access_token")
        if not isinstance(token, str) or not token:
            raise Ga4Error("google_error", "no access token in Google's answer")
        return token

    async def run_report(self, body: dict[str, Any]) -> dict[str, Any]:
        url = f"{get_settings().GA4_API_URL}properties/{quote(self.property_id)}:runReport"
        for attempt in range(2):
            if self._token is None:
                self._token = await self._fetch_token()
            try:
                response = await self.http.post(
                    url, json=body, headers={"Authorization": f"Bearer {self._token}"}
                )
            except httpx.HTTPError as exc:
                raise Ga4Error("unreachable") from exc
            # A token can expire during a long run: one new token, then give up.
            if response.status_code == 401 and attempt == 0:
                self._token = None
                continue
            if response.status_code != 200:
                raise _google_error(response)
            return response.json()
        raise Ga4Error("key_rejected")


def path_variants(url: str) -> list[str]:
    """The page's path as Google Analytics may have recorded it: with and without the
    trailing slash, and decoded if it was percent-encoded. Their views are summed."""
    path = urlsplit(url.strip()).path or "/"
    variants: list[str] = []
    for base in (path, unquote(path)):
        bare = base.rstrip("/") or "/"
        for candidate in (bare, bare if bare == "/" else f"{bare}/"):
            if candidate not in variants:
                variants.append(candidate)
    return variants


def report_body(host: str, paths: list[str], start: date, end: date) -> dict[str, Any]:
    return {
        "dateRanges": [{"startDate": start.isoformat(), "endDate": end.isoformat()}],
        "dimensions": [{"name": "hostName"}, {"name": "pagePath"}],
        "metrics": [{"name": METRIC}],
        "dimensionFilter": {
            "andGroup": {
                "expressions": [
                    {
                        "filter": {
                            "fieldName": "hostName",
                            "stringFilter": {"matchType": "EXACT", "value": host},
                        }
                    },
                    {"filter": {"fieldName": "pagePath", "inListFilter": {"values": paths}}},
                ]
            }
        },
        "limit": 100,
    }


def total_views(report: dict[str, Any]) -> int | None:
    """The sum over the report's rows, or None when it has none (missing, never 0)."""
    rows = report.get("rows") or []
    if not rows:
        return None
    total = 0
    for row in rows:
        try:
            total += int(row["metricValues"][0]["value"])
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise Ga4Error("google_error", "a row without a number") from exc
    return total


def window(release_date: date, days: int) -> tuple[date, date]:
    """The release day and the days after it: day 0 to day 27 for a 28-day checkpoint."""
    return release_date, release_date + timedelta(days=max(days, 1) - 1)


def window_closed(release_date: date, days: int, today: date) -> bool:
    return release_date + timedelta(days=days + PROCESSING_LAG_DAYS) <= today


async def test_connection(
    account: ServiceAccount, property_id: str, host: str | None, today: date
) -> dict[str, Any]:
    """A one-day report for yesterday. The answer says in plain words what failed."""
    day = today - timedelta(days=1)
    body: dict[str, Any] = {
        "dateRanges": [{"startDate": day.isoformat(), "endDate": day.isoformat()}],
        "metrics": [{"name": METRIC}],
    }
    if host:
        body["dimensionFilter"] = {
            "filter": {
                "fieldName": "hostName",
                "stringFilter": {"matchType": "EXACT", "value": host},
            }
        }
    result: dict[str, Any] = {"date": day.isoformat(), "host": host}
    try:
        async with Client(account, property_id) as client:
            views = total_views(await client.run_report(body)) or 0
    except Ga4Error as exc:
        return {**result, "ok": False, "code": exc.code, "detail": exc.detail}
    code = "connected" if views else "connected_no_views"
    return {**result, "ok": True, "code": code, "views": views, "detail": None}


# ---------------------------------------------------------------- the job


@dataclass
class Candidate:
    reading_id: uuid.UUID
    release_id: uuid.UUID
    code: str | None
    website_url: str
    release_date: date
    days: int


async def candidates(
    db: AsyncSession, institution_id: uuid.UUID, domain: str | None, today: date
) -> tuple[list[Candidate], list[Candidate]]:
    """Releases whose website views are still missing: (window closed, still open).

    Missing means nothing was fetched and no one entered a number or N/A: a person's entry
    is never fetched over (P4).
    """
    rows = await db.execute(
        select(
            Reading.id,
            Release.id,
            Release.code,
            Release.website_url,
            Release.release_date,
            Checkpoint.offset_days,
        )
        .join(Measure, Measure.id == Reading.measure_id)
        .join(Checkpoint, Checkpoint.id == Measure.checkpoint_id)
        .join(Release, Release.id == Reading.release_id)
        .where(
            Release.institution_id == institution_id,
            Release.deleted_at.is_(None),
            Release.release_date.is_not(None),
            Measure.source == SOURCE,
            Measure.is_active.is_(True),
            Reading.state == STATE_MISSING,
        )
        .order_by(Release.release_date, Release.code)
    )
    closed: list[Candidate] = []
    still_open: list[Candidate] = []
    for reading_id, release_id, code, url, released, days in rows.all():
        if not url_on_domain(url, domain):
            continue
        candidate = Candidate(reading_id, release_id, code, url, released, days)
        (closed if window_closed(released, days, today) else still_open).append(candidate)
    return closed, still_open


async def _store(candidate: Candidate, views: int) -> bool:
    """Write one fetched number, unless the release or the reading changed meanwhile."""
    async with SessionLocal() as db:
        audit.set_note(db, AUDIT_NOTE)
        reading = await db.scalar(
            select(Reading)
            .where(Reading.id == candidate.reading_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        release = await db.get(Release, candidate.release_id)
        if (
            reading is None
            or release is None
            or reading.state != STATE_MISSING
            or release.deleted_at is not None
            or release.website_url != candidate.website_url
            or release.release_date != candidate.release_date
        ):
            return False
        reading.value = Decimal(views)
        reading.state = STATE_VALUE
        reading.source = SOURCE_AUTO
        reading.version += 1
        reading.entered_by_id = None
        reading.entered_at = datetime.now(UTC)
        await db.commit()
    return True


def _codes(items: list[str | None]) -> str:
    shown = [code or "—" for code in items[:20]]
    more = f", and {len(items) - 20} more" if len(items) > 20 else ""
    return f" ({', '.join(shown)}{more})" if items else ""


async def fetch_website_views(*, manual: bool) -> JobResult:
    """One run of the job, daily or from Fetch now. See the module's docstring."""
    async with SessionLocal() as db:
        institution = await get_institution(db)
        integration = await load_integration(db, institution.id)
        try:
            account = stored_account(integration)
        except Ga4Error as exc:
            return JobResult("skipped", reason(exc.code))
        property_id = (integration.config or {}).get("property_id")
        if not property_id:
            return JobResult("skipped", reason("no_property"))
        if not institution.website_domain:
            return JobResult("skipped", reason("no_domain"))
        if not manual and integration.first_fetch_at is None:
            return JobResult("skipped", reason("waiting_for_first_fetch"))
        domain = institution.website_domain.strip().lower()
        today = today_in(institution.timezone)
        institution_id, integration_id = institution.id, integration.id

    # A session-level lock, held for the whole run, so Fetch now and the daily run never
    # fetch side by side. Released on every way out.
    async with engine.connect() as lock:
        key = lock_key(f"{SOURCE}:{institution_id}")
        if not await lock.scalar(select(func.pg_try_advisory_lock(key))):
            return JobResult("skipped", reason("busy"))
        try:
            return await _fetch(
                institution_id, integration_id, account, property_id, domain, today, manual
            )
        finally:
            await lock.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
            await lock.commit()


async def _fetch(
    institution_id: uuid.UUID,
    integration_id: uuid.UUID,
    account: ServiceAccount,
    property_id: str,
    domain: str,
    today: date,
    manual: bool,
) -> JobResult:
    async with SessionLocal() as db:
        due, still_open = await candidates(db, institution_id, domain, today)

    fetched = 0
    no_data: list[str | None] = []
    skipped: list[str | None] = []
    errors: list[str] = []
    stopped: Ga4Error | None = None
    async with Client(account, property_id) as client:
        for candidate in due:
            start, end = window(candidate.release_date, candidate.days)
            body = report_body(domain, path_variants(candidate.website_url), start, end)
            try:
                views = total_views(await client.run_report(body))
            except Ga4Error as exc:
                if exc.code in FATAL:
                    stopped = exc
                    break
                errors.append(f"{candidate.code or '—'}: {reason(exc.code, exc.detail)}")
                continue
            if views is None:
                no_data.append(candidate.code)
            elif await _store(candidate, views):
                fetched += 1
            else:
                skipped.append(candidate.code)

    if manual and stopped is None:
        async with SessionLocal() as db:
            integration = await db.get(Integration, integration_id)
            if integration is not None and integration.first_fetch_at is None:
                integration.first_fetch_at = datetime.now(UTC)
                await db.commit()

    parts = [
        f"Fetched {fetched}.",
        f"No data for this path: {len(no_data)}{_codes(no_data)}.",
        f"Skipped, changed during the run: {len(skipped)}{_codes(skipped)}.",
    ]
    if still_open:
        parts.append(f"Not yet due (28 days and 2 days' processing): {len(still_open)}.")
    if errors:
        parts.append(f"Errors: {len(errors)}: " + "; ".join(errors[:5]) + ".")
    if stopped is not None:
        parts.insert(0, f"Stopped: {reason(stopped.code, stopped.detail)}")
    logger.info(
        "Website views: fetched %d, no data %d, errors %d", fetched, len(no_data), len(errors)
    )
    status = "failed" if stopped is not None or errors else "succeeded"
    return JobResult(status, " ".join(parts))
