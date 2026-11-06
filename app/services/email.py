"""Email delivery through aiosmtplib, with bilingual templates.

Message bodies are never logged: they can hold temporary passwords and reset
links, which are credentials. The Media Monitor logged them; that is not ported.
"""

import logging
from email.message import EmailMessage
from html import escape

import aiosmtplib

from app.config import get_settings
from app.i18n import normalise_language, t
from app.services.theme import load_theme

logger = logging.getLogger(__name__)

SMTP_TIMEOUT_SECONDS = 20


async def send_email(to: str, subject: str, body_html: str, body_text: str) -> bool:
    """Send one message. Returns False, with the reason logged, if it could not be sent."""
    settings = get_settings()
    if not settings.smtp_configured:
        logger.warning("Email not sent: SMTP is not configured")
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.SMTP_FROM
    message["To"] = to
    message.set_content(body_text)
    message.add_alternative(body_html, subtype="html")

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER or None,
            password=settings.SMTP_PASSWORD or None,
            use_tls=settings.SMTP_SECURITY == "ssl",
            start_tls=settings.SMTP_SECURITY == "starttls",
            timeout=SMTP_TIMEOUT_SECONDS,
        )
    except Exception as exc:  # noqa: BLE001 - delivery problems must not break the request
        logger.error("Email delivery failed: %s", type(exc).__name__)
        return False
    logger.info("Email delivered")
    return True


def _layout(language: str, blocks: list[str]) -> str:
    """Wrap HTML blocks in the shared layout, coloured by the active theme."""
    tokens = load_theme().tokens
    return (
        f'<!DOCTYPE html><html lang="{language}"><body style="margin:0;padding:24px;'
        f"font-family:sans-serif;color:{tokens['text-primary']};"
        f'background:{tokens["surface-primary"]}">'
        '<div style="max-width:520px;margin:0 auto">'
        f'<h2 style="color:{tokens["text-accent"]};font-weight:600">'
        f"{escape(t(language, 'email.product'))}</h2>"
        f"{''.join(blocks)}"
        f'<hr style="border:none;border-top:1px solid {tokens["border-disabled"]};margin:24px 0">'
        f'<p style="font-size:12px;color:{tokens["text-secondary"]}">'
        f"{escape(t(language, 'email.footer'))}</p>"
        "</div></body></html>"
    )


def _button(label: str, url: str) -> str:
    tokens = load_theme().tokens
    return (
        f'<p><a href="{escape(url, quote=True)}" style="display:inline-block;padding:10px 18px;'
        f"border-radius:6px;background:{tokens['surface-accent']};"
        f'color:{tokens["text-on-accent"]};text-decoration:none">{escape(label)}</a></p>'
    )


async def send_password_reset_email(
    to: str, language: str | None, reset_url: str, expires_minutes: int
) -> bool:
    lang = normalise_language(language)
    intro = t(lang, "email.reset.intro")
    expiry = t(lang, "email.reset.expiry", minutes=expires_minutes)
    ignore = t(lang, "email.reset.ignore")
    body_text = "\n\n".join([intro, reset_url, expiry, ignore, t(lang, "email.footer")])
    body_html = _layout(
        lang,
        [
            f"<p>{escape(intro)}</p>",
            _button(t(lang, "email.reset.button"), reset_url),
            f"<p>{escape(expiry)}</p>",
            f"<p>{escape(ignore)}</p>",
        ],
    )
    return await send_email(to, t(lang, "email.reset.subject"), body_html, body_text)


async def send_welcome_email(
    to: str, language: str | None, initial_password: str, login_url: str
) -> bool:
    lang = normalise_language(language)
    intro = t(lang, "email.welcome.intro")
    email_label = t(lang, "email.welcome.email_label")
    password_label = t(lang, "email.welcome.password_label")
    notice = t(lang, "email.welcome.change_notice")
    body_text = "\n\n".join(
        [
            intro,
            f"{email_label}: {to}\n{password_label}: {initial_password}",
            login_url,
            notice,
            t(lang, "email.footer"),
        ]
    )
    body_html = _layout(
        lang,
        [
            f"<p>{escape(intro)}</p>",
            f"<p>{escape(email_label)}: {escape(to)}<br>"
            f"{escape(password_label)}: <code>{escape(initial_password)}</code></p>",
            _button(t(lang, "email.welcome.button"), login_url),
            f"<p>{escape(notice)}</p>",
        ],
    )
    return await send_email(to, t(lang, "email.welcome.subject"), body_html, body_text)
