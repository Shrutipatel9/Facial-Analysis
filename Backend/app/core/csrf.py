"""CSRF defenses for cookie-authenticated endpoints.

Browser APIs that rely on the httpOnly refresh cookie (notably
POST /auth/refresh) are CSRF-sensitive. Bearer-protected routes are not,
because a cross-site form cannot set the Authorization header.

Defense in depth (OWASP-aligned for SPAs):
1. Require ``X-Requested-With: XMLHttpRequest`` — simple HTML form CSRF
   cannot set custom headers (triggers a CORS preflight that fails).
2. When ``Origin`` (or ``Referer``) is present, it must match the
   configured CORS allow-list (``CORS_ORIGINS``).
"""

from urllib.parse import urlparse

from fastapi import Request

from app.core.config import get_settings
from app.exceptions import CsrfRejectedError

_REQUESTED_WITH = "XMLHttpRequest"


def _origin_from_referer(referer: str) -> str | None:
    parsed = urlparse(referer)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def assert_cookie_request_allowed(request: Request) -> None:
    """Raise CsrfRejectedError unless the request looks like our SPA."""
    requested_with = request.headers.get("x-requested-with")
    if requested_with != _REQUESTED_WITH:
        raise CsrfRejectedError()

    settings = get_settings()
    allowed = set(settings.cors_origins)

    origin = request.headers.get("origin")
    if origin is None:
        referer = request.headers.get("referer")
        if referer:
            origin = _origin_from_referer(referer)

    # Same-origin fetch via the Next.js rewrite usually sends Origin.
    # If both Origin and Referer are absent (non-browser clients / some
    # proxies), the custom header above is still required — that alone
    # blocks classic form CSRF.
    if origin is not None and origin not in allowed:
        raise CsrfRejectedError()
