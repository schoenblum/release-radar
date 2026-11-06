"""Security headers on every response (BRIEF section 5.5).

The policy allows same-origin resources only. Nothing in the app needs more:
fonts are self-hosted, the Vite build inlines nothing, and React sets styles
through the DOM, which ``style-src`` does not restrict.
"""

from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings

CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' data:",
        "font-src 'self'",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)
# The development-only API docs load their page from a CDN.
_DEVELOPMENT_DOC_PATHS = ("/docs", "/openapi.json")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        settings = get_settings()
        is_docs = not settings.is_production and request.url.path.startswith(_DEVELOPMENT_DOC_PATHS)
        if not is_docs:
            response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        # Reset links carry a token in the URL. It must not leak through a referrer.
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if settings.cookie_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response
