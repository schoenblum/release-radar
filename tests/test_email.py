"""Email delivery settings and templates."""

import logging

import pytest

from app.config import get_settings
from app.services.email import send_email, send_password_reset_email, send_welcome_email
from tests.conftest import plain_body


@pytest.mark.parametrize(
    ("security", "use_tls", "start_tls"),
    [("starttls", False, True), ("ssl", True, False), ("none", False, False)],
)
async def test_connection_security_setting(outbox, monkeypatch, security, use_tls, start_tls):
    monkeypatch.setattr(get_settings(), "SMTP_SECURITY", security)
    assert await send_email("to@example.org", "Subject", "<p>Hi</p>", "Hi") is True
    _, options = outbox[0]
    assert options["use_tls"] is use_tls
    assert options["start_tls"] is start_tls
    assert options["hostname"] == "smtp.example.org"


async def test_smtp_login_is_used_when_configured(outbox, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "SMTP_USER", "relay-user")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "relay-password")
    await send_email("to@example.org", "Subject", "<p>Hi</p>", "Hi")
    _, options = outbox[0]
    assert options["username"] == "relay-user"
    assert options["password"] == "relay-password"


async def test_unconfigured_smtp_returns_false():
    assert await send_email("to@example.org", "Subject", "<p>Hi</p>", "Hi") is False


async def test_delivery_failure_returns_false_and_logs_no_content(outbox, monkeypatch, caplog):
    async def refuse(*_args, **_kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr("app.services.email.aiosmtplib.send", refuse)
    with caplog.at_level(logging.DEBUG):
        result = await send_email("to@example.org", "Subject", "<p>secret-body</p>", "secret-body")
    assert result is False
    assert "secret-body" not in caplog.text
    assert "to@example.org" not in caplog.text


async def test_welcome_email_in_japanese(outbox):
    await send_welcome_email("to@example.org", "ja", "temp-pass-123", "http://rr.test/login")
    message, _ = outbox[0]
    assert message["Subject"] == "Release Radar のアカウントを作成しました"
    body = plain_body(message)
    assert "仮パスワード: temp-pass-123" in body
    assert "http://rr.test/login" in body


async def test_unknown_or_missing_language_falls_back_to_english(outbox):
    await send_welcome_email("to@example.org", None, "temp-pass-123", "http://rr.test/login")
    await send_password_reset_email("to@example.org", "de", "http://rr.test/reset", 60)
    assert outbox[0][0]["Subject"] == "Your Release Radar account is ready"
    assert outbox[1][0]["Subject"] == "Reset your Release Radar password"


async def test_html_body_escapes_values_and_uses_theme_colours(outbox):
    await send_welcome_email(
        "to@example.org", "en", "<script>alert(1)</script>", "http://rr.test/login"
    )
    html = outbox[0][0].get_body(preferencelist=("html",)).get_content()
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "#33556B" in html
