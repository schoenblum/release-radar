"""Website views from Google Analytics (R8.1.1). A fake Google answers; nothing reaches the real
one. The service-account key is generated for the run and never written anywhere."""

import json
from datetime import timedelta
from decimal import Decimal
from urllib.parse import parse_qs

import httpx
import jwt
import pytest
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from sqlalchemy import func, select, text

from app.config import get_settings
from app.database import SessionLocal, engine
from app.models import AuditLog, Institution, Integration, JobRun, Measure, Reading, Release
from app.models.integration import KIND_GA4
from app.services import ga4, scheduler
from app.services.audit import REDACTED
from app.services.readings import today_in

URL = "/api/v1/integrations/ga4"
DOMAIN = "news.example.org"
PROPERTY = "123456789"


@pytest.fixture(scope="module")
def rsa_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _pem(key) -> str:
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()


@pytest.fixture
def key_file(rsa_key) -> str:
    """A key file shaped like Google's download, with synthetic values."""
    return json.dumps(
        dict(
            type="service_account",
            project_id="example-project",
            private_key_id="0123456789abcdef",
            private_key=_pem(rsa_key),
            client_email="ga4-reader@example-project.example.org",
            client_id="100000000000000000001",
            token_uri="https://token.example.org/should-not-be-used",
        )
    )


class FakeGoogle:
    """Google's token endpoint and runReport, as far as Release Radar uses them."""

    def __init__(self, public_key) -> None:
        self.public_key = public_key
        # Views per (host, path).
        self.views: dict[tuple[str, str], int] = {}
        self.token_error: tuple[int, dict] | None = None
        self.report_error: tuple[int, dict] | None = None
        self.error_for_path: dict[str, tuple[int, dict]] = {}
        self.reports: list[dict] = []
        self.token_requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if str(request.url) == get_settings().GOOGLE_TOKEN_URL:
            self.token_requests.append(request)
            if self.token_error:
                return httpx.Response(self.token_error[0], json=self.token_error[1])
            form = parse_qs(request.content.decode())
            assert form["grant_type"] == ["urn:ietf:params:oauth:grant-type:jwt-bearer"]
            # Signed with the key's private key, for its address and the read-only scope.
            claims = jwt.decode(
                form["assertion"][0],
                self.public_key,
                algorithms=["RS256"],
                audience=get_settings().GOOGLE_TOKEN_URL,
            )
            assert claims["iss"] == "ga4-reader@example-project.example.org"
            assert claims["scope"] == ga4.SCOPE
            return httpx.Response(200, json={"access_token": "fake-token", "expires_in": 3599})
        assert str(request.url) == (f"{get_settings().GA4_API_URL}properties/{PROPERTY}:runReport")
        assert request.headers["Authorization"] == "Bearer fake-token"
        body = json.loads(request.content)
        self.reports.append(body)
        if self.report_error:
            return httpx.Response(self.report_error[0], json=self.report_error[1])
        if "dimensions" not in body:
            # Test connection: one day, the host only.
            total = sum(views for (host, _), views in self.views.items() if host == DOMAIN)
            return httpx.Response(200, json={"rows": [{"metricValues": [{"value": str(total)}]}]})
        host_filter, path_filter = body["dimensionFilter"]["andGroup"]["expressions"]
        host = host_filter["filter"]["stringFilter"]["value"]
        paths = path_filter["filter"]["inListFilter"]["values"]
        for path in paths:
            if path in self.error_for_path:
                status, error = self.error_for_path[path]
                return httpx.Response(status, json=error)
        rows = [
            {
                "dimensionValues": [{"value": host}, {"value": path}],
                "metricValues": [{"value": str(self.views[(host, path)])}],
            }
            for path in paths
            if (host, path) in self.views
        ]
        return httpx.Response(200, json={"rows": rows} if rows else {"rowCount": 0})


@pytest.fixture
def google(monkeypatch, rsa_key) -> FakeGoogle:
    fake = FakeGoogle(rsa_key.public_key())
    monkeypatch.setattr(ga4, "_transport", httpx.MockTransport(fake))
    return fake


def _error(status: str, message: str, reason: str | None = None) -> dict:
    details = [{"@type": "type.googleapis.com/google.rpc.ErrorInfo", "reason": reason}]
    return {"error": {"status": status, "message": message, "details": details if reason else []}}


async def _connect(client, headers, key_file, property_id=PROPERTY) -> dict:
    response = await client.put(f"{URL}/key", json={"key": key_file}, headers=headers)
    assert response.status_code == 200, response.text
    if property_id is not None:
        response = await client.patch(
            URL, json={"field": "property_id", "value": property_id, "version": 0}, headers=headers
        )
        assert response.status_code == 200, response.text
    return (await client.get(URL, headers=headers)).json()


async def _today():
    async with SessionLocal() as db:
        return today_in((await db.scalar(select(Institution))).timezone)


async def _release(days_ago: int, path: str = "/news/a-paper/", **values) -> Release:
    async with SessionLocal() as db:
        institution_id = await db.scalar(select(Institution.id))
        release = Release(
            institution_id=institution_id,
            title=values.pop("title", f"Synthetic release {path}"),
            release_date=(await _today()) - timedelta(days=days_ago),
            website_url=values.pop("website_url", f"https://{DOMAIN}{path}"),
            **values,
        )
        db.add(release)
        await db.commit()
        return release


async def _views(release: Release) -> Reading:
    async with SessionLocal() as db:
        return await db.scalar(
            select(Reading)
            .join(Measure, Measure.id == Reading.measure_id)
            .where(Reading.release_id == release.id, Measure.key == "hp_views.d28")
        )


async def _last_run() -> JobRun:
    async with SessionLocal() as db:
        return await db.scalar(select(JobRun).order_by(JobRun.started_at.desc()).limit(1))


async def _integration() -> Integration:
    async with SessionLocal() as db:
        return await db.scalar(select(Integration).where(Integration.kind == KIND_GA4))


# ---------------------------------------------------------------- the key


def test_a_downloaded_key_is_read(key_file):
    account = ga4.parse_key(key_file)
    assert account.client_email == "ga4-reader@example-project.example.org"
    assert account.shown() == {
        "client_email": "ga4-reader@example-project.example.org",
        "project_id": "example-project",
    }


@pytest.mark.parametrize(
    ("change", "code"),
    [
        (lambda data: "not json at all", "key_not_json"),
        (lambda data: json.dumps([data]), "key_not_service_account"),
        (lambda data: json.dumps({**data, "type": "authorized_user"}), "key_not_service_account"),
        (
            lambda data: json.dumps({k: v for k, v in data.items() if k != "private_key"}),
            "key_incomplete",
        ),
        (lambda data: json.dumps({**data, "client_email": "nobody"}), "key_incomplete"),
        (
            lambda data: json.dumps({**data, "private_key": "-----not a key-----"}),
            "key_bad_private_key",
        ),
    ],
)
def test_a_file_that_is_not_a_service_account_key_is_explained(key_file, change, code):
    with pytest.raises(ga4.Ga4Error) as caught:
        ga4.parse_key(change(json.loads(key_file)))
    assert caught.value.code == code


def test_a_key_that_is_not_rsa_is_refused(key_file):
    other = _pem(ec.generate_private_key(ec.SECP256R1()))
    with pytest.raises(ga4.Ga4Error) as caught:
        ga4.parse_key(json.dumps({**json.loads(key_file), "private_key": other}))
    assert caught.value.code == "key_bad_private_key"


async def test_the_key_is_stored_encrypted_and_never_shown(client, admin_headers, key_file):
    status = await _connect(client, admin_headers, key_file)
    assert status["configured"] is True and status["readable"] is True
    assert status["client_email"] == "ga4-reader@example-project.example.org"
    assert status["property_id"] == PROPERTY
    shown = json.dumps(status)
    assert "PRIVATE KEY" not in shown and "0123456789abcdef" not in shown

    integration = await _integration()
    assert b"PRIVATE KEY" not in integration.credential
    async with engine.connect() as connection:
        raw = await connection.scalar(text("SELECT integrations::text FROM integrations"))
    assert "PRIVATE KEY" not in raw and "private_key" not in raw
    async with SessionLocal() as db:
        entries = list(
            await db.scalars(select(AuditLog).where(AuditLog.entity_id == integration.id))
        )
    assert entries
    assert "PRIVATE KEY" not in json.dumps([[e.old_value, e.new_value] for e in entries])
    created = next(entry for entry in entries if entry.action == "create")
    assert created.new_value.get("credential", REDACTED) == REDACTED


async def test_a_bad_file_is_refused_with_its_reason_and_not_echoed(client, admin_headers):
    response = await client.put(
        f"{URL}/key", json={"key": '{"type": "x", "secret": "s3cr3t"}'}, headers=admin_headers
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "ga4_key_not_service_account"
    assert "s3cr3t" not in response.text
    assert (await client.get(URL, headers=admin_headers)).json()["configured"] is False


@pytest.mark.parametrize("role", ["editor", "viewer"])
async def test_integrations_are_for_admins(client, headers_for, key_file, role):
    from app.models import UserRole

    headers = await headers_for(UserRole(role))
    assert (await client.get(URL, headers=headers)).status_code == 403
    assert (
        await client.put(f"{URL}/key", json={"key": key_file}, headers=headers)
    ).status_code == 403
    assert (await client.post(f"{URL}/fetch", headers=headers)).status_code == 403
    assert (await client.post(f"{URL}/test", headers=headers)).status_code == 403


@pytest.mark.parametrize(
    ("value", "stored"),
    [("123456789", "123456789"), ("properties/987654321", "987654321"), (" 42 ", "42")],
)
async def test_the_property_id_is_digits(client, admin_headers, value, stored):
    response = await client.patch(
        URL, json={"field": "property_id", "value": value, "version": 0}, headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json() == {"field": "property_id", "value": stored, "version": 1}


async def test_a_property_id_with_letters_is_explained(client, admin_headers):
    response = await client.patch(
        URL, json={"field": "property_id", "value": "G-ABC123", "version": 0}, headers=admin_headers
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "ga4_property_digits"


async def test_a_stale_property_id_save_is_a_conflict(client, admin_headers):
    body = {"field": "property_id", "value": "111", "version": 0}
    assert (await client.patch(URL, json=body, headers=admin_headers)).status_code == 200
    response = await client.patch(URL, json={**body, "value": "222"}, headers=admin_headers)
    assert response.status_code == 409
    assert response.json()["current_value"] == "111"


async def test_removing_the_key_keeps_the_property_and_the_numbers(client, admin_headers, key_file):
    await _connect(client, admin_headers, key_file)
    status = (await client.delete(f"{URL}/key", headers=admin_headers)).json()
    assert status["configured"] is False
    assert status["client_email"] is None
    assert status["property_id"] == PROPERTY


async def test_a_key_stored_on_another_install_is_reported_not_raised(
    client, admin_headers, key_file
):
    await _connect(client, admin_headers, key_file)
    async with SessionLocal() as db:
        integration = await db.scalar(select(Integration))
        integration.credential = Fernet(Fernet.generate_key()).encrypt(key_file.encode())
        await db.commit()

    status = (await client.get(URL, headers=admin_headers)).json()
    assert status["configured"] is True and status["readable"] is False

    response = await client.post(f"{URL}/test", headers=admin_headers)
    assert response.status_code == 409
    assert response.json()["detail"] == "ga4_key_unreadable"

    result = await ga4.fetch_website_views(manual=True)
    assert result.status == "skipped"
    assert result.detail.startswith("The stored key cannot be read on this install; enter it")


async def test_the_full_export_leaves_the_integration_out(client, admin_headers, key_file):
    await _connect(client, admin_headers, key_file)
    response = await client.get("/api/v1/settings/export?format=json", headers=admin_headers)
    assert "integrations" not in response.json()
    # The audit log is in it, with the address the page shows, but never the key.
    assert "PRIVATE KEY" not in response.text and "0123456789abcdef" not in response.text


# ---------------------------------------------------------------- test connection


async def test_test_connection_reports_the_views_of_one_day(
    client, admin_headers, key_file, google
):
    google.views[(DOMAIN, "/news/x/")] = 41
    await _connect(client, admin_headers, key_file)
    result = (await client.post(f"{URL}/test", headers=admin_headers)).json()
    assert result["ok"] is True
    assert result["code"] == "connected"
    assert result["views"] == 41
    assert result["host"] == DOMAIN
    day = (await _today()) - timedelta(days=1)
    assert google.reports[-1]["dateRanges"] == [
        {"startDate": day.isoformat(), "endDate": day.isoformat()}
    ]
    # The key file's own token address is never used.
    assert all("should-not-be-used" not in str(r.url) for r in google.token_requests)
    status = (await client.get(URL, headers=admin_headers)).json()
    assert status["last_test"]["code"] == "connected"


async def test_test_connection_with_no_views_says_so(client, admin_headers, key_file, google):
    await _connect(client, admin_headers, key_file)
    result = (await client.post(f"{URL}/test", headers=admin_headers)).json()
    assert result["ok"] is True and result["code"] == "connected_no_views"


@pytest.mark.parametrize(
    ("status", "error", "code"),
    [
        (
            403,
            _error(
                "PERMISSION_DENIED",
                "Google Analytics Data API has not been used in project 1 before or it is "
                "disabled.",
                "SERVICE_DISABLED",
            ),
            "api_disabled",
        ),
        (
            403,
            _error(
                "PERMISSION_DENIED", "User does not have sufficient permissions for this property."
            ),
            "no_access",
        ),
        (400, _error("INVALID_ARGUMENT", "Invalid property ID: 12."), "wrong_property"),
        (429, _error("RESOURCE_EXHAUSTED", "Exhausted property tokens."), "quota"),
        (500, _error("INTERNAL", "Something broke."), "google_error"),
    ],
)
async def test_test_connection_explains_what_failed(
    client, admin_headers, key_file, google, status, error, code
):
    google.report_error = (status, error)
    await _connect(client, admin_headers, key_file)
    result = (await client.post(f"{URL}/test", headers=admin_headers)).json()
    assert result["ok"] is False
    assert result["code"] == code


async def test_a_key_google_refuses_is_explained(client, admin_headers, key_file, google):
    google.token_error = (
        400,
        {"error": "invalid_grant", "error_description": "Invalid JWT Signature."},
    )
    await _connect(client, admin_headers, key_file)
    result = (await client.post(f"{URL}/test", headers=admin_headers)).json()
    assert result["code"] == "key_rejected"
    assert result["detail"] == "Invalid JWT Signature."


async def test_google_out_of_reach_is_explained(client, admin_headers, key_file, monkeypatch):
    def unreachable(request):
        raise httpx.ConnectError("no route", request=request)

    monkeypatch.setattr(ga4, "_transport", httpx.MockTransport(unreachable))
    await _connect(client, admin_headers, key_file)
    result = (await client.post(f"{URL}/test", headers=admin_headers)).json()
    assert result["code"] == "unreachable"


async def test_test_connection_needs_a_property(client, admin_headers, key_file):
    await _connect(client, admin_headers, key_file, property_id=None)
    response = await client.post(f"{URL}/test", headers=admin_headers)
    assert response.status_code == 409
    assert response.json()["detail"] == "ga4_no_property"


# ---------------------------------------------------------------- the job


def test_paths_are_tried_with_and_without_the_trailing_slash():
    assert ga4.path_variants("https://news.example.org/news/a/b/") == ["/news/a/b", "/news/a/b/"]
    assert ga4.path_variants("https://news.example.org/news/a.html?x=1") == [
        "/news/a.html",
        "/news/a.html/",
    ]
    assert ga4.path_variants("https://news.example.org/") == ["/"]
    assert ga4.path_variants("https://news.example.org/news/%E7%A0%94/") == [
        "/news/%E7%A0%94",
        "/news/%E7%A0%94/",
        "/news/研",
        "/news/研/",
    ]


async def test_without_a_key_the_job_is_skipped_with_the_reason():
    result = await ga4.fetch_website_views(manual=False)
    assert result.status == "skipped"
    assert "No Google Analytics key is stored" in result.detail


async def test_daily_runs_wait_for_the_first_fetch_now(client, admin_headers, key_file, google):
    await _connect(client, admin_headers, key_file)
    release = await _release(40)
    google.views[(DOMAIN, "/news/a-paper/")] = 10

    result = await ga4.fetch_website_views(manual=False)
    assert result.status == "skipped"
    assert "after the first Fetch now" in result.detail
    assert (await _views(release)).state == "missing"
    assert google.reports == []


async def test_fetch_now_backfills_and_daily_runs_follow(client, admin_headers, key_file, google):
    await _connect(client, admin_headers, key_file)
    closed = await _release(40, "/news/closed/")
    edge = await _release(30, "/news/edge/")
    still_open = await _release(29, "/news/open/")
    no_data = await _release(45, "/news/nobody-came/", title="No data")
    off_domain = await _release(50, website_url="https://www.example.org/old/1/")
    google.views[(DOMAIN, "/news/closed")] = 100
    google.views[(DOMAIN, "/news/closed/")] = 23
    google.views[(DOMAIN, "/news/edge/")] = 7
    google.views[(DOMAIN, "/news/open/")] = 5

    response = await client.post(f"{URL}/fetch", headers=admin_headers)
    assert response.status_code == 202

    run = await _last_run()
    assert run.job_key == scheduler.JOB_GA4_MANUAL
    assert run.status == "succeeded"
    assert run.detail.startswith("Fetched 2. No data for this path: 1")
    assert "Not yet due (28 days and 2 days' processing): 1." in run.detail

    reading = await _views(closed)
    assert (reading.state, reading.value, reading.source) == ("value", Decimal(123), "auto")
    assert reading.entered_by_id is None
    assert (await _views(edge)).value == Decimal(7)
    assert (await _views(still_open)).state == "missing"
    # No rows: still missing, never 0.
    assert (await _views(no_data)).state == "missing"
    assert (await _views(off_domain)).state == "not_applicable"

    # The release's 28 days, on the institution's host, the path with and without the slash.
    body = next(r for r in google.reports if "/news/closed" in json.dumps(r))
    start = closed.release_date
    assert body["dateRanges"] == [
        {
            "startDate": start.isoformat(),
            "endDate": (start + timedelta(days=27)).isoformat(),
        }
    ]
    host, paths = body["dimensionFilter"]["andGroup"]["expressions"]
    assert host["filter"]["stringFilter"] == {"matchType": "EXACT", "value": DOMAIN}
    assert paths["filter"]["inListFilter"]["values"] == ["/news/closed", "/news/closed/"]
    assert body["metrics"] == [{"name": "screenPageViews"}]

    # The audit log says where the number came from.
    async with SessionLocal() as db:
        notes = set(await db.scalars(select(AuditLog.note).where(AuditLog.entity_id == reading.id)))
    assert ga4.AUDIT_NOTE in notes

    status = (await client.get(URL, headers=admin_headers)).json()
    assert status["fetched"] == 2
    assert [item["title"] for item in status["waiting"]] == ["No data"]
    assert status["not_yet_due"] == 1
    assert status["first_fetch_at"] is not None
    assert status["last_run"]["status"] == "succeeded"

    # Daily runs now go ahead, and only ask for what is still missing.
    google.reports.clear()
    result = await ga4.fetch_website_views(manual=False)
    assert result.status == "succeeded"
    assert len(google.reports) == 1
    assert result.detail.startswith("Fetched 0. No data for this path: 1")


async def test_a_persons_number_or_na_is_never_fetched_over(
    client, admin_headers, headers_for, key_file, google
):
    from app.models import UserRole

    await _connect(client, admin_headers, key_file)
    typed = await _release(40, "/news/typed/")
    marked = await _release(40, "/news/marked/")
    google.views[(DOMAIN, "/news/typed/")] = 99
    google.views[(DOMAIN, "/news/marked/")] = 99
    editor = await headers_for(UserRole.editor)
    reading = await _views(typed)
    await client.patch(
        f"/api/v1/readings/{reading.id}",
        json={"version": reading.version, "value": 12},
        headers=editor,
    )
    reading = await _views(marked)
    await client.patch(
        f"/api/v1/readings/{reading.id}",
        json={"version": reading.version, "state": "not_applicable"},
        headers=editor,
    )

    await ga4.fetch_website_views(manual=True)
    assert (await _views(typed)).value == Decimal(12)
    assert (await _views(typed)).source == "manual"
    assert (await _views(marked)).state == "not_applicable"
    assert google.reports == []


async def test_changing_the_page_or_the_date_clears_a_fetched_number(
    client, admin_headers, key_file, google
):
    await _connect(client, admin_headers, key_file)
    moved = await _release(40, "/news/before/")
    redated = await _release(40, "/news/redated/")
    google.views[(DOMAIN, "/news/before/")] = 50
    google.views[(DOMAIN, "/news/redated/")] = 60
    await ga4.fetch_website_views(manual=True)
    assert (await _views(moved)).value == Decimal(50)

    async with SessionLocal() as db:
        (await db.get(Release, moved.id)).website_url = f"https://{DOMAIN}/news/after/"
        (await db.get(Release, redated.id)).release_date = redated.release_date - timedelta(1)
        await db.commit()
    assert (await _views(moved)).state == "missing"
    assert (await _views(redated)).state == "missing"

    # The next run fetches it again, for the new page.
    google.views[(DOMAIN, "/news/after/")] = 8
    await ga4.fetch_website_views(manual=False)
    assert (await _views(moved)).value == Decimal(8)


async def test_a_typed_number_survives_a_change_of_page(client, admin_headers, headers_for):
    from app.models import UserRole

    release = await _release(40, "/news/typed/")
    reading = await _views(release)
    editor = await headers_for(UserRole.editor)
    await client.patch(
        f"/api/v1/readings/{reading.id}",
        json={"version": reading.version, "value": 12},
        headers=editor,
    )
    async with SessionLocal() as db:
        (await db.get(Release, release.id)).website_url = f"https://{DOMAIN}/news/moved/"
        await db.commit()
    assert (await _views(release)).value == Decimal(12)


async def test_a_fetched_number_moved_off_the_domain_goes_not_applicable(
    client, admin_headers, key_file, google
):
    await _connect(client, admin_headers, key_file)
    release = await _release(40, "/news/a/")
    google.views[(DOMAIN, "/news/a/")] = 50
    await ga4.fetch_website_views(manual=True)
    async with SessionLocal() as db:
        (await db.get(Release, release.id)).website_url = "https://www.example.org/old/"
        await db.commit()
    reading = await _views(release)
    assert (reading.state, reading.source) == ("not_applicable", "auto")


async def test_a_refused_key_stops_the_run_with_the_reason(client, admin_headers, key_file, google):
    await _connect(client, admin_headers, key_file)
    await _release(40, "/news/a/")
    await _release(41, "/news/b/")
    google.report_error = (403, _error("PERMISSION_DENIED", "No permission for this property."))

    result = await ga4.fetch_website_views(manual=True)
    assert result.status == "failed"
    assert result.detail.startswith("Stopped: The service account has no access")
    # Stopped at the first, not tried for each.
    assert len(google.reports) == 1
    # A failed first fetch does not start the daily ones.
    assert (await _integration()).first_fetch_at is None


async def test_one_page_failing_does_not_stop_the_others(client, admin_headers, key_file, google):
    await _connect(client, admin_headers, key_file)
    await _release(40, "/news/broken/", title="Broken")
    fine = await _release(41, "/news/fine/")
    google.error_for_path["/news/broken"] = (500, _error("INTERNAL", "Backend error."))
    google.views[(DOMAIN, "/news/fine/")] = 3

    result = await ga4.fetch_website_views(manual=True)
    assert result.status == "failed"
    assert "Fetched 1." in result.detail
    assert "Errors: 1:" in result.detail and "Backend error." in result.detail
    assert (await _views(fine)).value == Decimal(3)


async def test_a_release_changed_during_the_run_is_left_alone(
    client, admin_headers, key_file, google, monkeypatch
):
    await _connect(client, admin_headers, key_file)
    release = await _release(40, "/news/a/")
    google.views[(DOMAIN, "/news/a/")] = 50
    original_store = ga4._store

    async def store(candidate, views):
        # Someone types a number while Google answers.
        async with SessionLocal() as db:
            reading = await db.get(Reading, candidate.reading_id)
            reading.value, reading.state, reading.source = Decimal(5), "value", "manual"
            await db.commit()
        return await original_store(candidate, views)

    monkeypatch.setattr(ga4, "_store", store)

    result = await ga4.fetch_website_views(manual=True)
    assert "Skipped, changed during the run: 1" in result.detail
    assert (await _views(release)).value == Decimal(5)


async def test_only_one_fetch_runs_at_a_time(client, admin_headers, key_file, google):
    await _connect(client, admin_headers, key_file)
    async with SessionLocal() as db:
        institution_id = await db.scalar(select(Institution.id))
    key = scheduler.lock_key(f"{ga4.SOURCE}:{institution_id}")
    async with engine.connect() as other:
        assert await other.scalar(select(func.pg_try_advisory_lock(key)))
        result = await ga4.fetch_website_views(manual=True)
        await other.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
        await other.commit()
    assert result.status == "skipped"
    assert result.detail == "Another fetch of website views is running."
    # And the lock is free again afterwards.
    assert (await ga4.fetch_website_views(manual=True)).status == "succeeded"


async def test_fetch_now_needs_a_key_and_a_property(client, admin_headers, key_file):
    response = await client.post(f"{URL}/fetch", headers=admin_headers)
    assert response.status_code == 409
    assert response.json()["detail"] == "ga4_no_key"
    await _connect(client, admin_headers, key_file, property_id=None)
    response = await client.post(f"{URL}/fetch", headers=admin_headers)
    assert response.json()["detail"] == "ga4_no_property"


async def test_without_a_website_domain_the_job_says_so(client, admin_headers, key_file):
    await _connect(client, admin_headers, key_file)
    async with SessionLocal() as db:
        (await db.scalar(select(Institution))).website_domain = None
        await db.commit()
    result = await ga4.fetch_website_views(manual=True)
    assert result.status == "skipped"
    assert "No website domain is set" in result.detail
