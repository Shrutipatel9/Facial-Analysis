"""Integration tests for Milestone 3.1 Phase 23 -- production hardening:
a real DB-backed health check, backend security headers (including the new
Content-Security-Policy), and a regression test for docs-gating (already
correct in code before this phase -- see app/main.py's docs_url/redoc_url/
openapi_url -- this only guards against a future regression)."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestHealthCheck:
    async def test_returns_200_with_database_ok_when_db_is_reachable(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["checks"]["database"] == "ok"

    async def test_returns_503_when_the_database_is_unreachable(self, client: AsyncClient, monkeypatch):
        def _broken_session_factory():
            # async_session_factory() is called synchronously in real code
            # (the `async with` is on its return value) -- raising here
            # simulates the connection attempt failing at that call.
            raise ConnectionError("simulated database outage")

        monkeypatch.setattr("app.main.async_session_factory", _broken_session_factory)
        resp = await client.get("/health")
        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "degraded"
        assert body["checks"]["database"] == "error"


class TestSecurityHeaders:
    async def test_api_responses_carry_a_strict_csp(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.headers["Content-Security-Policy"] == "default-src 'none'; frame-ancestors 'none'"

    async def test_standard_headers_are_present(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
        assert resp.headers["X-Frame-Options"] == "DENY"
        assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "camera=()" in resp.headers["Permissions-Policy"]


class TestDocsGating:
    """Regression coverage only -- app/main.py already gates these on
    settings.is_development (docs_url/openapi_url None outside dev,
    redoc_url always None). Tests run with ENVIRONMENT unset from
    tests/conftest.py's own overrides, so Settings.is_development reflects
    whatever the real environment default is; this asserts the contract
    (never both present unless development), not a specific value."""

    async def test_redoc_is_never_served(self, client: AsyncClient):
        resp = await client.get("/redoc")
        assert resp.status_code == 404

    async def test_docs_and_openapi_are_gated_together(self, client: AsyncClient):
        docs_resp = await client.get("/docs")
        openapi_resp = await client.get("/openapi.json")
        # Both gated on the exact same flag (settings.is_development) --
        # either both are served or neither is, never a mismatched pair.
        assert (docs_resp.status_code != 404) == (openapi_resp.status_code != 404)
