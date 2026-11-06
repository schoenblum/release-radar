"""Sign-in, sessions, password changes and resets."""

import logging
import re
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy import select, update

from app.config import get_settings
from app.database import SessionLocal
from app.models import PasswordResetToken, RefreshToken, User
from app.services import rate_limit
from tests.conftest import BOOTSTRAP_EMAIL, BOOTSTRAP_PASSWORD, bearer, plain_body, sign_in

PASSWORD = "correct-horse-battery"
NEW_PASSWORD = "a-brand-new-passphrase"


@pytest.fixture
def frozen_rate_window(monkeypatch):
    """Keep all hits in one window, so a test cannot straddle a window boundary."""
    window = datetime(2026, 1, 1, tzinfo=UTC)
    monkeypatch.setattr(rate_limit, "_window_start", lambda _seconds, _now=None: window)


async def test_login_returns_token_and_sets_a_protected_cookie(client, make_user):
    await make_user()
    response = await client.post(
        "/api/v1/auth/login", json={"email": "EDITOR@example.org", "password": PASSWORD}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["user"]["email"] == "editor@example.org"
    assert "password_hash" not in body["user"]

    cookie = response.headers["set-cookie"].lower()
    assert "rr_refresh=" in cookie
    assert "httponly" in cookie
    assert "samesite=strict" in cookie
    assert "path=/api/v1/auth" in cookie


async def test_refresh_token_is_stored_only_as_a_hash(client, make_user):
    await make_user()
    await sign_in(client, "editor@example.org", PASSWORD)
    raw = client.cookies["rr_refresh"]
    async with SessionLocal() as db:
        stored = await db.scalar(select(RefreshToken.token_hash))
    assert stored != raw
    assert len(stored) == 64


@pytest.mark.parametrize(
    ("email", "password"),
    [("editor@example.org", "wrong-password"), ("nobody@example.org", PASSWORD)],
)
async def test_failed_login_gives_the_same_answer_for_any_reason(
    client, make_user, email, password
):
    await make_user()
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 401
    assert response.json() == {"detail": "invalid_credentials"}


async def test_inactive_user_cannot_sign_in(client, make_user):
    await make_user(is_active=False)
    response = await client.post(
        "/api/v1/auth/login", json={"email": "editor@example.org", "password": PASSWORD}
    )
    assert response.status_code == 401


async def test_validation_errors_do_not_echo_the_password(client):
    response = await client.post(
        "/api/v1/auth/login", json={"email": "not-an-email", "password": "my-secret-value"}
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "validation_error"
    assert "my-secret-value" not in response.text


async def test_me_requires_a_token(client):
    assert (await client.get("/api/v1/auth/me")).status_code == 401


@pytest.mark.parametrize(
    "claims",
    [
        {"typ": "refresh", "tv": 0},
        {"typ": "access", "tv": 99},
        {"typ": "access", "tv": 0, "expired": True},
    ],
)
async def test_unsuitable_tokens_are_rejected(client, make_user, claims):
    user = await make_user()
    settings = get_settings()
    now = datetime.now(UTC)
    expired = claims.pop("expired", False)
    expires = now - timedelta(minutes=1) if expired else now + timedelta(hours=1)
    token = jwt.encode(
        {"sub": str(user.id), "exp": expires, **claims},
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    assert (await client.get("/api/v1/auth/me", headers=bearer(token))).status_code == 401


async def test_unsigned_token_is_rejected(client, make_user):
    user = await make_user()
    token = jwt.encode({"sub": str(user.id), "typ": "access", "tv": 0}, key="", algorithm="none")
    assert (await client.get("/api/v1/auth/me", headers=bearer(token))).status_code == 401


async def test_refresh_issues_a_working_token_and_extends_the_session(client, make_user):
    await make_user()
    await sign_in(client, "editor@example.org", PASSWORD)
    async with SessionLocal() as db:
        before = await db.scalar(select(RefreshToken.expires_at))

    response = await client.post("/api/v1/auth/refresh")

    assert response.status_code == 200
    token = response.json()["access_token"]
    assert (await client.get("/api/v1/auth/me", headers=bearer(token))).status_code == 200
    async with SessionLocal() as db:
        assert await db.scalar(select(RefreshToken.expires_at)) >= before


async def test_refresh_without_a_session_is_refused(client):
    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 401
    assert response.json() == {"detail": "session_expired"}


async def test_expired_session_cannot_refresh(client, make_user):
    await make_user()
    await sign_in(client, "editor@example.org", PASSWORD)
    async with SessionLocal() as db:
        await db.execute(
            update(RefreshToken).values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )
        await db.commit()
    assert (await client.post("/api/v1/auth/refresh")).status_code == 401


async def test_logout_revokes_only_this_session(client, make_user):
    await make_user()
    await sign_in(client, "editor@example.org", PASSWORD)
    first_cookie = client.cookies["rr_refresh"]
    client.cookies.clear()
    await sign_in(client, "editor@example.org", PASSWORD)
    second_cookie = client.cookies["rr_refresh"]

    client.cookies.clear()
    client.cookies.set("rr_refresh", first_cookie, domain="rr.test", path="/api/v1/auth")
    assert (await client.post("/api/v1/auth/logout")).status_code == 204
    assert "rr_refresh" not in client.cookies

    client.cookies.set("rr_refresh", first_cookie, domain="rr.test", path="/api/v1/auth")
    assert (await client.post("/api/v1/auth/refresh")).status_code == 401

    client.cookies.clear()
    client.cookies.set("rr_refresh", second_cookie, domain="rr.test", path="/api/v1/auth")
    assert (await client.post("/api/v1/auth/refresh")).status_code == 200


async def test_forced_password_change_blocks_the_api_but_not_the_change(client, make_user):
    """The first admin's temporary password opens nothing but the password page."""
    body = await sign_in(client, BOOTSTRAP_EMAIL, BOOTSTRAP_PASSWORD)
    assert body["user"]["force_password_change"] is True
    headers = bearer(body["access_token"])

    blocked = await client.get("/api/v1/users", headers=headers)
    assert blocked.status_code == 403
    assert blocked.json() == {"detail": "password_change_required"}
    assert (await client.get("/api/v1/auth/me", headers=headers)).status_code == 200
    language = await client.patch("/api/v1/users/me", headers=headers, json={"language": "ja"})
    assert language.status_code == 200

    changed = await client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": BOOTSTRAP_PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert changed.status_code == 200
    assert changed.json()["user"]["force_password_change"] is False

    new_headers = bearer(changed.json()["access_token"])
    assert (await client.get("/api/v1/users", headers=new_headers)).status_code == 200


async def test_change_password_ends_other_sessions_and_keeps_this_one(client, make_user):
    await make_user()
    other = await sign_in(client, "editor@example.org", PASSWORD)
    other_cookie = client.cookies["rr_refresh"]
    client.cookies.clear()
    this = await sign_in(client, "editor@example.org", PASSWORD)

    response = await client.post(
        "/api/v1/auth/change-password",
        headers=bearer(this["access_token"]),
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert response.status_code == 200

    # The other device's access token and session both stop working at once.
    stale = await client.get("/api/v1/auth/me", headers=bearer(other["access_token"]))
    assert stale.status_code == 401
    kept_cookie = client.cookies["rr_refresh"]
    client.cookies.clear()
    client.cookies.set("rr_refresh", other_cookie, domain="rr.test", path="/api/v1/auth")
    assert (await client.post("/api/v1/auth/refresh")).status_code == 401

    # This device stays signed in.
    client.cookies.clear()
    client.cookies.set("rr_refresh", kept_cookie, domain="rr.test", path="/api/v1/auth")
    assert (await client.post("/api/v1/auth/refresh")).status_code == 200
    fresh = await client.get("/api/v1/auth/me", headers=bearer(response.json()["access_token"]))
    assert fresh.status_code == 200

    # The old password no longer works, the new one does.
    client.cookies.clear()
    old = await client.post(
        "/api/v1/auth/login", json={"email": "editor@example.org", "password": PASSWORD}
    )
    assert old.status_code == 401
    await sign_in(client, "editor@example.org", NEW_PASSWORD)


@pytest.mark.parametrize(
    ("current", "new", "status", "code"),
    [
        ("wrong-password", NEW_PASSWORD, 400, "current_password_incorrect"),
        (PASSWORD, "short", 422, "password_too_short"),
        (PASSWORD, "あ" * 25, 422, "password_too_long"),
        (PASSWORD, PASSWORD, 422, "password_unchanged"),
    ],
)
async def test_rejected_password_changes_explain_why(client, make_user, current, new, status, code):
    await make_user()
    body = await sign_in(client, "editor@example.org", PASSWORD)
    response = await client.post(
        "/api/v1/auth/change-password",
        headers=bearer(body["access_token"]),
        json={"current_password": current, "new_password": new},
    )
    assert response.status_code == status
    assert response.json() == {"detail": code}


async def _request_reset_token(client, outbox, email="editor@example.org") -> str:
    response = await client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert response.status_code == 202
    assert response.json() == {"email_enabled": True}
    return re.search(r"token=([\w-]+)", plain_body(outbox[-1][0])).group(1)


async def test_password_reset_by_email(client, make_user, outbox):
    await make_user()
    signed_in = await sign_in(client, "editor@example.org", PASSWORD)
    token = await _request_reset_token(client, outbox)

    message = outbox[-1][0]
    assert message["To"] == "editor@example.org"
    assert "http://rr.test/reset-password?token=" in plain_body(message)

    response = await client.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": NEW_PASSWORD}
    )
    assert response.status_code == 204

    # Sessions from before the reset have ended.
    stale = await client.get("/api/v1/auth/me", headers=bearer(signed_in["access_token"]))
    assert stale.status_code == 401
    assert (await client.post("/api/v1/auth/refresh")).status_code == 401
    await sign_in(client, "editor@example.org", NEW_PASSWORD)

    # The link works only once.
    again = await client.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": "yet-another-password"}
    )
    assert again.status_code == 400
    assert again.json() == {"detail": "reset_token_invalid"}


async def test_reset_email_follows_the_users_language(client, make_user, outbox):
    await make_user(language="ja")
    await client.post("/api/v1/auth/forgot-password", json={"email": "editor@example.org"})
    message = outbox[-1][0]
    assert message["Subject"] == "Release Radar のパスワード再設定"
    assert "このリンクは 1 回のみ" in plain_body(message)


async def test_reset_also_clears_a_forced_password_change(client, make_user, outbox):
    await make_user(force_password_change=True)
    token = await _request_reset_token(client, outbox)
    await client.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": NEW_PASSWORD}
    )
    assert (await sign_in(client, "editor@example.org", NEW_PASSWORD))["user"][
        "force_password_change"
    ] is False


async def test_new_reset_link_replaces_the_previous_one(client, make_user, outbox):
    await make_user()
    first = await _request_reset_token(client, outbox)
    await _request_reset_token(client, outbox)
    response = await client.post(
        "/api/v1/auth/reset-password", json={"token": first, "new_password": NEW_PASSWORD}
    )
    assert response.status_code == 400


async def test_expired_reset_link_is_refused(client, make_user, outbox):
    await make_user()
    token = await _request_reset_token(client, outbox)
    async with SessionLocal() as db:
        await db.execute(
            update(PasswordResetToken).values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )
        await db.commit()
    response = await client.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": NEW_PASSWORD}
    )
    assert response.status_code == 400


async def test_forgot_password_does_not_reveal_which_addresses_exist(client, make_user, outbox):
    await make_user()
    known = await client.post("/api/v1/auth/forgot-password", json={"email": "editor@example.org"})
    unknown = await client.post(
        "/api/v1/auth/forgot-password", json={"email": "nobody@example.org"}
    )
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert len(outbox) == 1


async def test_forgot_password_says_so_when_email_is_off(client, make_user):
    await make_user()
    response = await client.post(
        "/api/v1/auth/forgot-password", json={"email": "editor@example.org"}
    )
    assert response.status_code == 202
    assert response.json() == {"email_enabled": False}
    async with SessionLocal() as db:
        assert await db.scalar(select(PasswordResetToken.id)) is None


async def test_credentials_never_reach_the_logs(client, make_user, outbox, admin_headers, caplog):
    await make_user()
    with caplog.at_level(logging.DEBUG):
        token = await _request_reset_token(client, outbox)
        created = await client.post(
            "/api/v1/users", headers=admin_headers, json={"email": "new@example.org"}
        )
    assert created.status_code == 201
    temporary = re.search(r"(?:Temporary password): (\S+)", plain_body(outbox[-1][0])).group(1)
    assert token not in caplog.text
    assert temporary not in caplog.text


@pytest.mark.usefixtures("frozen_rate_window")
async def test_repeated_failures_lock_the_pair_but_not_other_accounts(client, make_user):
    await make_user()
    await make_user("colleague@example.org")
    wrong = {"email": "editor@example.org", "password": "wrong-password"}
    for _ in range(10):
        assert (await client.post("/api/v1/auth/login", json=wrong)).status_code == 401

    blocked = await client.post("/api/v1/auth/login", json=wrong)
    assert blocked.status_code == 429
    assert blocked.json() == {"detail": "rate_limited"}
    assert int(blocked.headers["retry-after"]) > 0

    # Even the right password has to wait, while a colleague in the same office can sign in.
    right = await client.post(
        "/api/v1/auth/login", json={"email": "editor@example.org", "password": PASSWORD}
    )
    assert right.status_code == 429
    await sign_in(client, "colleague@example.org", PASSWORD)


@pytest.mark.usefixtures("frozen_rate_window")
async def test_successful_logins_are_not_counted(client, make_user):
    await make_user()
    for _ in range(12):
        await sign_in(client, "editor@example.org", PASSWORD)


@pytest.mark.usefixtures("frozen_rate_window")
async def test_reset_mail_per_account_is_limited_without_changing_the_answer(
    client, make_user, outbox
):
    await make_user()
    for _ in range(5):
        response = await client.post(
            "/api/v1/auth/forgot-password", json={"email": "editor@example.org"}
        )
        assert response.status_code == 202
    assert len(outbox) == 3


@pytest.mark.usefixtures("frozen_rate_window")
async def test_reset_attempts_from_one_address_are_limited(client):
    for _ in range(20):
        response = await client.post(
            "/api/v1/auth/reset-password", json={"token": "guess", "new_password": NEW_PASSWORD}
        )
        assert response.status_code == 400
    response = await client.post(
        "/api/v1/auth/reset-password", json={"token": "guess", "new_password": NEW_PASSWORD}
    )
    assert response.status_code == 429


async def test_deactivating_a_user_ends_access_at_once(client, make_user, admin_headers):
    user: User = await make_user()
    client.cookies.clear()
    signed_in = await sign_in(client, "editor@example.org", PASSWORD)

    response = await client.patch(
        f"/api/v1/users/{user.id}", headers=admin_headers, json={"is_active": False}
    )
    assert response.status_code == 200

    stale = await client.get("/api/v1/auth/me", headers=bearer(signed_in["access_token"]))
    assert stale.status_code == 401
    assert (await client.post("/api/v1/auth/refresh")).status_code == 401
