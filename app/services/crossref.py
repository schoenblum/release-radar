"""Looks up papers by DOI at Crossref (step 1.4).

Following Crossref's etiquette, requests name the tool and, if the institution has set one,
its contact address: an office address from Settings, never a person's. A lookup only ever
fills in. If Crossref is unreachable or does not know the DOI, the answer says so and nothing
else is held up (P4).
"""

import html
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any
from urllib.parse import quote, unquote

import httpx

from app import __version__
from app.config import get_settings

logger = logging.getLogger("release-radar.crossref")

PROJECT_URL = "https://github.com/schoenblum/release-radar"
FOUND = "found"
NOT_FOUND = "not_found"
UNAVAILABLE = "unavailable"
# Replaced in tests, so that the suite never reaches the real service.
_transport: httpx.AsyncBaseTransport | None = None

_TIMEOUT = httpx.Timeout(6.0, connect=3.0)
_DOI = re.compile(r"^10\.\d{4,9}/\S+$")
_DOI_PREFIX = re.compile(r"^(https?://(dx\.|www\.)?doi\.org/|doi:\s*)", re.IGNORECASE)
_MARKUP = re.compile(r"<[^>]+>")
_ORCID = re.compile(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")
# The earliest public date first. A date with no day is not a date we can use.
_DATE_FIELDS = ("published", "published-online", "published-print", "issued")


def normalise_doi(value: str) -> str | None:
    """The bare, lowercase DOI (R7.5.7), or None if this is not one. Forgives what copying from
    a paper brings along: a "DOI:" label before a doi.org link, and a full stop at the end."""
    doi = value.strip()
    for _ in range(2):
        doi = _DOI_PREFIX.sub("", doi).strip()
    # Some sites link a DOI with its slash encoded: 10.1038%2Fs41586-026-01234-5.
    if "%" in doi:
        doi = unquote(doi)
    doi = doi.rstrip(".,;").lower()
    return doi if _DOI.match(doi) and len(doi) <= 255 else None


@dataclass(frozen=True)
class Paper:
    journal: str | None = None
    paper_title: str | None = None
    publication_date: date | None = None
    authors: list[dict[str, str | None]] = field(default_factory=list)


@dataclass(frozen=True)
class Lookup:
    status: str
    paper: Paper | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"status": self.status, **asdict(self.paper or Paper())}


def _clean(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    # Titles can carry markup such as <i> and encoded characters.
    return " ".join(html.unescape(_MARKUP.sub("", value)).split()) or None


def _first(values: Any) -> str | None:
    return _clean(values[0]) if isinstance(values, list) and values else None


def _full_date(work: dict[str, Any]) -> date | None:
    for name in _DATE_FIELDS:
        parts = (work.get(name) or {}).get("date-parts") or [[]]
        if len(parts[0]) == 3 and all(isinstance(part, int) for part in parts[0]):
            try:
                return date(*parts[0])
            except ValueError:
                continue
    return None


def _author(entry: dict[str, Any]) -> dict[str, str | None]:
    orcid = _ORCID.search(entry.get("ORCID") or "")
    return {
        "given": _clean(entry.get("given")),
        "family": _clean(entry.get("family")),
        # An organisation has only a name.
        "name": _clean(entry.get("name")),
        "orcid": orcid.group(0) if orcid else None,
    }


def parse_work(work: dict[str, Any]) -> Paper:
    return Paper(
        journal=_first(work.get("container-title")),
        paper_title=_first(work.get("title")),
        publication_date=_full_date(work),
        authors=[_author(entry) for entry in work.get("author") or [] if isinstance(entry, dict)],
    )


def user_agent(contact_email: str | None) -> str:
    contact = f"; mailto:{contact_email}" if contact_email else ""
    return f"ReleaseRadar/{__version__} ({PROJECT_URL}{contact})"


async def lookup(doi: str, contact_email: str | None) -> Lookup:
    """Fetch a paper. Never raises: a failed lookup must not stop anyone's work."""
    try:
        async with httpx.AsyncClient(
            timeout=_TIMEOUT,
            transport=_transport,
            follow_redirects=True,
            headers={"User-Agent": user_agent(contact_email)},
        ) as client:
            response = await client.get(get_settings().CROSSREF_API_URL + quote(doi, safe=""))
        if response.status_code == httpx.codes.NOT_FOUND:
            return Lookup(NOT_FOUND)
        response.raise_for_status()
        return Lookup(FOUND, parse_work(response.json()["message"]))
    except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError) as exc:
        logger.warning("Crossref lookup failed: %s", type(exc).__name__)
        return Lookup(UNAVAILABLE)
