"""HTTP security headers for direct hits to the FastAPI origin.

The Next.js frontend also sets its own headers (see frontend/next.config.ts).
This middleware covers clients that talk to the API without the proxy.
"""

from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings

# Docs/schema routes (app/main.py's docs_url/redoc_url/openapi_url, dev-only
# already) render/serve HTML+inline scripts for Swagger UI -- the strict API
# CSP below would break them, so they're excluded rather than the policy
# being loosened for every route to accommodate a dev-only surface.
_DOCS_PATHS = frozenset({"/docs", "/redoc", "/openapi.json"})
# This is a pure JSON API, never an HTML-rendering surface in production
# (see _DOCS_PATHS above for the one dev-only exception) -- a much
# stricter policy than the frontend's own necessarily looser one
# (frontend/next.config.ts, which has to allow Next.js's inline
# hydration scripts) is appropriate here: nothing on this origin should
# ever load a script, style, or frame.
_API_CSP = "default-src 'none'; frame-ancestors 'none'"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        settings = get_settings()

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=()",
        )
        response.headers.setdefault("X-XSS-Protection", "0")  # modern browsers: rely on CSP
        response.headers.setdefault("Cache-Control", "no-store")
        if request.url.path not in _DOCS_PATHS:
            response.headers.setdefault("Content-Security-Policy", _API_CSP)

        if not settings.is_development:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=63072000; includeSubDomains; preload",
            )

        return response
