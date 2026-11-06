"""Health, security headers, frontend serving, setup and configuration."""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError
from sqlalchemy import func, select

from app import __version__, main
from app.bootstrap import bootstrap
from app.cli import reset_password
from app.config import Settings, get_settings
from app.database import SessionLocal
from app.i18n import normalise_language, t
from app.models import Institution, User, UserRole
from app.services import crypto
from tests.conftest import BOOTSTRAP_EMAIL, ROOT, bearer, sign_in


async def test_health(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}


async def test_health_reports_an_unreachable_database(client, monkeypatch):
    class Unreachable:
        async def __aenter__(self):
            raise OSError("connection refused")

        async def __aexit__(self, *_args):
            return False

    monkeypatch.setattr(main, "SessionLocal", Unreachable)
    response = await client.get("/api/v1/health")
    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert "refused" not in response.text


async def test_security_headers_on_every_response(client):
    for path in ("/api/v1/health", "/brand/theme.css", "/some-page"):
        headers = (await client.get(path)).headers
        policy = headers["content-security-policy"]
        assert "default-src 'self'" in policy
        assert "script-src 'self'" in policy
        assert "frame-ancestors 'none'" in policy
        assert "unsafe" not in policy
        assert headers["x-content-type-options"] == "nosniff"
        assert headers["x-frame-options"] == "DENY"
        assert headers["referrer-policy"] == "no-referrer"


async def test_api_responses_are_not_cached(client):
    assert (await client.get("/api/v1/health")).headers["cache-control"] == "no-store"


async def test_hsts_only_over_https(client, monkeypatch):
    assert "strict-transport-security" not in (await client.get("/api/v1/health")).headers
    monkeypatch.setattr(get_settings(), "BASE_URL", "https://radar.example.org")
    assert "strict-transport-security" in (await client.get("/api/v1/health")).headers


async def test_session_cookie_is_secure_over_https(client, make_user, monkeypatch):
    await make_user()
    monkeypatch.setattr(get_settings(), "BASE_URL", "https://radar.example.org")
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "editor@example.org", "password": "correct-horse-battery"},
    )
    assert "secure" in response.headers["set-cookie"].lower()


def test_api_docs_are_off_in_production():
    code = (
        "from app.main import app;"
        "assert app.docs_url is None and app.redoc_url is None and app.openapi_url is None"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        env={**os.environ, "ENVIRONMENT": "production"},
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


async def test_unknown_api_path_is_a_json_404(client):
    response = await client.get("/api/v1/nothing-here")
    assert response.status_code == 404
    assert response.json() == {"detail": "not_found"}


@pytest.fixture
def built_frontend(tmp_path, monkeypatch) -> Path:
    (tmp_path / "index.html").write_text("<title>Release Radar</title>")
    (tmp_path / "robots.txt").write_text("static file")
    monkeypatch.setattr(main, "STATIC_DIR", tmp_path)
    monkeypatch.setattr(main, "INDEX_FILE", tmp_path / "index.html")
    return tmp_path


async def test_client_side_routes_get_the_frontend(client, built_frontend):
    for path in ("/", "/my-releases", "/reset-password"):
        response = await client.get(path)
        assert response.status_code == 200
        assert "Release Radar" in response.text
    assert (await client.get("/robots.txt")).text == "static file"


@pytest.mark.parametrize("path", ["/%2e%2e/secret.txt", "/..%2fsecret.txt", "/../secret.txt"])
async def test_paths_cannot_escape_the_static_folder(client, built_frontend, path):
    (built_frontend.parent / "secret.txt").write_text("do-not-serve")
    response = await client.get(path)
    assert "do-not-serve" not in response.text


async def test_missing_frontend_build_is_explained(client, tmp_path, monkeypatch):
    monkeypatch.setattr(main, "STATIC_DIR", tmp_path)
    monkeypatch.setattr(main, "INDEX_FILE", tmp_path / "index.html")
    response = await client.get("/")
    assert response.status_code == 503
    assert response.json() == {"detail": "frontend_not_built"}


async def test_bootstrap_creates_one_institution_and_one_admin_and_can_repeat():
    await bootstrap()
    await bootstrap()
    async with SessionLocal() as db:
        assert await db.scalar(select(func.count()).select_from(Institution)) == 1
        admins = list(await db.scalars(select(User).where(User.role == UserRole.admin)))
        institution = await db.scalar(select(Institution))
    assert [admin.email for admin in admins] == [BOOTSTRAP_EMAIL]
    assert admins[0].force_password_change is True
    assert admins[0].institution_id == institution.id
    assert institution.name_en == "Example University"
    assert institution.name_ja == "例大学"
    assert institution.timezone == "Asia/Tokyo"
    assert institution.ay_start_month == 4


async def test_bootstrap_without_admin_settings_explains_what_to_do(monkeypatch):
    async with SessionLocal() as db:
        await db.execute(User.__table__.delete())
        await db.commit()
    monkeypatch.setattr(get_settings(), "BOOTSTRAP_ADMIN_EMAIL", None)
    with pytest.raises(RuntimeError, match="BOOTSTRAP_ADMIN_EMAIL"):
        await bootstrap()


async def test_lockout_recovery_command(client, make_user, capsys):
    user = await make_user(is_active=False)
    assert await reset_password("EDITOR@example.org") == 0
    temporary = capsys.readouterr().out.split("Temporary password: ")[1].split()[0]

    body = await sign_in(client, "editor@example.org", temporary)
    assert body["user"]["force_password_change"] is True
    assert body["user"]["id"] == str(user.id)
    me = await client.get("/api/v1/auth/me", headers=bearer(body["access_token"]))
    assert me.status_code == 200


async def test_lockout_recovery_for_an_unknown_address(capsys):
    assert await reset_password("nobody@example.org") == 1
    assert "No account" in capsys.readouterr().err


def test_short_secret_key_is_refused():
    with pytest.raises(ValidationError):
        Settings(
            SECRET_KEY="too-short",
            DATABASE_URL="postgresql+asyncpg://user@localhost/db",
            FERNET_KEY=Fernet.generate_key().decode(),
        )


def test_fernet_round_trip_and_key_rotation(monkeypatch):
    settings = get_settings()
    old_key = settings.FERNET_KEY
    secret = crypto.encrypt("an-api-key")
    assert secret != b"an-api-key"
    assert crypto.decrypt(secret) == "an-api-key"

    # After rotation the new key is primary, and the old value stays readable.
    monkeypatch.setattr(settings, "FERNET_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(settings, "FERNET_KEYS", old_key)
    rotated_fernet = crypto._build_fernet()
    assert rotated_fernet.decrypt(secret).decode() == "an-api-key"

    # Re-encrypted under the new key, it no longer needs the old one.
    rotated = rotated_fernet.rotate(secret)
    monkeypatch.setattr(settings, "FERNET_KEYS", "")
    assert crypto._build_fernet().decrypt(rotated).decode() == "an-api-key"


def test_backend_messages_fall_back_and_fill_placeholders():
    assert normalise_language("ja") == "ja"
    assert normalise_language("de") == "en"
    assert normalise_language(None) == "en"
    assert "30" in t("ja", "email.reset.expiry", minutes=30)
    with pytest.raises(KeyError):
        t("en", "email.nothing_here")


def _load_i18n_checker():
    spec = importlib.util.spec_from_file_location(
        "check_i18n", os.path.join(ROOT, "scripts/check_i18n.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_i18n_checker_finds_each_kind_of_problem():
    compare = _load_i18n_checker().compare
    english = {"a": "Hello {{name}}", "b": "Bye", "c": "Fine"}
    japanese = {"a": "こんにちは", "c": " ", "d": "余分"}
    problems = "\n".join(compare("test", english, japanese))
    assert "b is missing from ja.json" in problems
    assert "d is missing from en.json" in problems
    assert "a has different placeholders" in problems
    assert "c is empty" in problems


def test_i18n_catalogues_are_in_order():
    result = subprocess.run(
        [sys.executable, "scripts/check_i18n.py"], cwd=ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def test_migrations_match_the_models():
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "check"], cwd=ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
