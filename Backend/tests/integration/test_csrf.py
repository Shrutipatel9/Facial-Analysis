"""CSRF guards on cookie-authenticated auth endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_refresh_without_x_requested_with_is_403():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Origin": "http://localhost:3000"},
    ) as client:
        resp = await client.post("/auth/refresh")

    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "CSRF_REJECTED"


@pytest.mark.asyncio
async def test_refresh_with_wrong_origin_is_403():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={
            "Origin": "https://evil.example",
            "X-Requested-With": "XMLHttpRequest",
        },
    ) as client:
        resp = await client.post("/auth/refresh")

    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "CSRF_REJECTED"


@pytest.mark.asyncio
async def test_refresh_with_valid_csrf_headers_and_no_cookie_is_401_not_403():
    """CSRF passes; missing cookie is a normal invalid-session 401."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={
            "Origin": "http://localhost:3000",
            "X-Requested-With": "XMLHttpRequest",
        },
    ) as client:
        resp = await client.post("/auth/refresh")

    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_TOKEN"
