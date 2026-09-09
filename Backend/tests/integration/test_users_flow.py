import pytest
from httpx import AsyncClient

from tests.integration.test_auth_flow import _register_and_verify

pytestmark = pytest.mark.asyncio


class TestGetMyProfile:
    async def test_get_me_returns_profile(self, client: AsyncClient, email_sender):
        tokens = await _register_and_verify(client, email_sender, "users-me@example.com")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        resp = await client.get("/users/me", headers=headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["email"] == "users-me@example.com"
        assert body["id"] == tokens["user"]["id"]
        assert body["full_name"] == "Test User"
        assert body["role"] == "user"
        assert body["verification_status"] == "verified"
        assert body["created_at"]

    async def test_unauthenticated_is_401(self, client: AsyncClient):
        resp = await client.get("/users/me")
        assert resp.status_code == 401
