"""Shared fixtures. The suite runs against a real PostgreSQL, because the app relies on
JSONB, advisory locks and ON CONFLICT. All data here is synthetic.

The test database is dropped and recreated on every run, so the suite refuses to start
unless the database name ends in ``_test``.
"""

import asyncio
import os
import subprocess
import sys
import tempfile
from urllib.parse import unquote

import asyncpg
from cryptography.fernet import Fernet
from sqlalchemy.engine.url import make_url

_TEST_URL = os.environ.get("TEST_DATABASE_URL")
if not _TEST_URL:
    raise RuntimeError("Set TEST_DATABASE_URL, for example via `docker compose run app-dev pytest`")
_PARSED_URL = make_url(_TEST_URL)
if not (_PARSED_URL.database or "").endswith("_test"):
    raise RuntimeError("Refusing to run: the test database name must end in _test")

BOOTSTRAP_EMAIL = "admin@example.org"
BOOTSTRAP_PASSWORD = "bootstrap-password"

# Set before the app is imported. Environment variables take priority over .env.
os.environ.update(
    {
        "ENVIRONMENT": "test",
        "DATABASE_URL": _TEST_URL,
        "BASE_URL": "http://rr.test",
        "SECRET_KEY": "test-only-signing-key-that-is-long-enough-for-hs256",
        "FERNET_KEY": Fernet.generate_key().decode(),
        "FERNET_KEYS": "",
        "BCRYPT_ROUNDS": "4",
        "BOOTSTRAP_ADMIN_EMAIL": BOOTSTRAP_EMAIL,
        "BOOTSTRAP_ADMIN_PASSWORD": BOOTSTRAP_PASSWORD,
        "INSTITUTION_NAME_EN": "Example University",
        "INSTITUTION_NAME_JA": "例大学",
        "INSTITUTION_TIMEZONE": "Asia/Tokyo",
        "INSTITUTION_WEBSITE_DOMAIN": "news.example.org",
        "INSTITUTION_CONTACT_EMAIL": "",
        "SMTP_HOST": "",
        "SMTP_PORT": "587",
        "SMTP_SECURITY": "starttls",
        "SMTP_USER": "",
        "SMTP_PASSWORD": "",
        "SMTP_FROM": "",
        "BACKUP_PASSPHRASE": "",
        "BACKUP_DIR": tempfile.mkdtemp(prefix="rr-test-backups-"),
        "BRAND_PACK_PATH": "/nonexistent-brand-pack",
        "SCHEDULER_ENABLED": "false",
    }
)

from collections.abc import AsyncIterator, Awaitable, Callable  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import select, text  # noqa: E402

from app.bootstrap import bootstrap  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Institution, User, UserRole  # noqa: E402
from app.services import crossref, ga4  # noqa: E402
from app.services.security import hash_password  # noqa: E402
from app.services.theme import load_theme  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def pg_env() -> dict[str, str]:
    """Environment for command-line Postgres tools talking to the test server."""
    return {**os.environ, "PGPASSWORD": _PARSED_URL.password or ""}


def pg_args(database: str | None = None) -> list[str]:
    return [
        "-h",
        _PARSED_URL.host or "localhost",
        "-p",
        str(_PARSED_URL.port or 5432),
        "-U",
        _PARSED_URL.username or "postgres",
        "-d",
        database or _PARSED_URL.database or "",
    ]


async def admin_connection() -> asyncpg.Connection:
    """A connection to the maintenance database, for creating and dropping databases."""
    return await asyncpg.connect(
        host=_PARSED_URL.host,
        port=_PARSED_URL.port or 5432,
        user=_PARSED_URL.username,
        password=_PARSED_URL.password,
        database="postgres",
    )


async def _recreate_database() -> None:
    connection = await admin_connection()
    try:
        name = _PARSED_URL.database
        await connection.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        await connection.execute(f'CREATE DATABASE "{name}"')
    finally:
        await connection.close()


@pytest.fixture(scope="session", autouse=True)
def _migrated_database() -> None:
    """Build the schema through the real migrations, which tests them as well."""
    asyncio.run(_recreate_database())
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True, cwd=ROOT)


@pytest_asyncio.fixture(autouse=True)
async def _clean_database() -> AsyncIterator[None]:
    tables = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    async with engine.begin() as connection:
        await connection.execute(text(f"TRUNCATE {tables} CASCADE"))
    await bootstrap()
    yield


@pytest.fixture(autouse=True)
def _fresh_theme() -> None:
    load_theme.cache_clear()


@pytest.fixture(autouse=True)
def crossref_answers(monkeypatch: pytest.MonkeyPatch) -> dict:
    """The suite never reaches the real Crossref. A test sets what it answers, by DOI."""
    answers: dict = {"status": 503, "works": {}, "requests": []}

    def answer(request: httpx.Request) -> httpx.Response:
        answers["requests"].append(request)
        doi = unquote(request.url.raw_path.decode().rsplit("/", 1)[1])
        if doi in answers["works"]:
            return httpx.Response(200, json={"message": answers["works"][doi]})
        return httpx.Response(answers["status"])

    monkeypatch.setattr(crossref, "_transport", httpx.MockTransport(answer))
    return answers


@pytest.fixture(autouse=True)
def _no_google(monkeypatch: pytest.MonkeyPatch) -> None:
    """The suite never reaches Google. ``tests/test_ga4.py`` puts a fake in its place."""
    monkeypatch.setattr(ga4, "_transport", httpx.MockTransport(lambda request: httpx.Response(503)))


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app, client=("198.51.100.7", 40000))
    async with AsyncClient(transport=transport, base_url="http://rr.test") as http:
        yield http


MakeUser = Callable[..., Awaitable[User]]


@pytest_asyncio.fixture
async def make_user() -> MakeUser:
    async def _make(
        email: str = "editor@example.org",
        password: str = "correct-horse-battery",
        role: UserRole = UserRole.editor,
        *,
        force_password_change: bool = False,
        is_active: bool = True,
        language: str | None = None,
    ) -> User:
        async with SessionLocal() as db:
            institution = await db.scalar(select(Institution).order_by(Institution.created_at))
            user = User(
                institution_id=institution.id,
                email=email,
                password_hash=hash_password(password),
                role=role,
                force_password_change=force_password_change,
                is_active=is_active,
                language=language,
            )
            db.add(user)
            await db.commit()
            return user

    return _make


async def sign_in(http: AsyncClient, email: str, password: str) -> dict:
    response = await http.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient, make_user: MakeUser) -> dict[str, str]:
    await make_user("chief@example.org", "chief-password-123", UserRole.admin)
    body = await sign_in(client, "chief@example.org", "chief-password-123")
    return bearer(body["access_token"])


@pytest_asyncio.fixture
async def headers_for(client: AsyncClient, make_user: MakeUser):
    """Sign in a new user with this role and return their request headers."""

    async def _headers(role: UserRole, email: str | None = None) -> dict[str, str]:
        address = email or f"{role.value}-account@example.org"
        await make_user(address, "correct-horse-battery", role)
        return bearer((await sign_in(client, address, "correct-horse-battery"))["access_token"])

    return _headers


@pytest.fixture
def outbox(monkeypatch: pytest.MonkeyPatch) -> list:
    """Turn email on and capture what would be sent, with its connection settings."""
    settings = get_settings()
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.org")
    monkeypatch.setattr(settings, "SMTP_FROM", "release-radar@example.org")
    sent: list = []

    async def fake_send(message, **options):
        sent.append((message, options))

    monkeypatch.setattr("app.services.email.aiosmtplib.send", fake_send)
    return sent


def plain_body(message) -> str:
    return message.get_body(preferencelist=("plain",)).get_content()
