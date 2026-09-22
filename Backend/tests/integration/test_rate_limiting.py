"""Integration tests for Milestone 3.1 Phase 21's rate limits on the three
paid-AI/payment trigger endpoints (POST /payments/checkout, POST /analysis,
POST /ai-visuals/{kind}) -- production hardening, closing a direct cost-
abuse surface (previously unlimited, see app/api/routers/*.py's own
docstrings). slowapi rejects an over-limit request in middleware, before
the route function's body -- and therefore before any service-layer call
-- ever runs, so these tests don't need realistic business-state setup
(a completed questionnaire, photos, a prior payment, ...): only an
authenticated user, so Depends(get_current_user) resolves before the
limiter check. Zero real AI/Stripe calls either way."""

import pytest
from httpx import AsyncClient

from tests.integration.test_auth_flow import _register_and_verify

pytestmark = pytest.mark.asyncio


async def _auth_headers(client: AsyncClient, email_sender, email: str) -> dict:
    tokens = await _register_and_verify(client, email_sender, email)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


class TestAnalysisTriggerRateLimit:
    async def test_sixth_request_within_the_hour_is_rate_limited(self, client: AsyncClient, email_sender):
        headers = await _auth_headers(client, email_sender, "ratelimit-analysis@example.com")
        responses = [await client.post("/analysis", headers=headers) for _ in range(6)]
        assert all(resp.status_code != 429 for resp in responses[:5])
        assert responses[5].status_code == 429
        assert responses[5].json()["error"]["code"] == "RATE_LIMITED"


class TestPaymentsCheckoutRateLimit:
    async def test_sixth_request_within_the_hour_is_rate_limited(self, client: AsyncClient, email_sender):
        headers = await _auth_headers(client, email_sender, "ratelimit-checkout@example.com")
        responses = [await client.post("/payments/checkout", headers=headers) for _ in range(6)]
        assert all(resp.status_code != 429 for resp in responses[:5])
        assert responses[5].status_code == 429
        assert responses[5].json()["error"]["code"] == "RATE_LIMITED"


class TestAiVisualsCreateRateLimit:
    async def test_eleventh_request_within_the_hour_is_rate_limited(self, client: AsyncClient, email_sender):
        headers = await _auth_headers(client, email_sender, "ratelimit-aivisuals@example.com")
        responses = [await client.post("/ai-visuals/hairstyle", headers=headers) for _ in range(11)]
        assert all(resp.status_code != 429 for resp in responses[:10])
        assert responses[10].status_code == 429
        assert responses[10].json()["error"]["code"] == "RATE_LIMITED"

    async def test_bucket_is_independent_per_kind(self, client: AsyncClient, email_sender):
        """slowapi's default key includes the request path, so each
        `{kind}` value gets its own independent 10/hour bucket -- 10 calls
        to hairstyle must not count against outfit's own separate limit."""
        headers = await _auth_headers(client, email_sender, "ratelimit-aivisuals-independent@example.com")
        hairstyle_responses = [await client.post("/ai-visuals/hairstyle", headers=headers) for _ in range(10)]
        assert all(resp.status_code != 429 for resp in hairstyle_responses)

        outfit_resp = await client.post("/ai-visuals/outfit", headers=headers)
        assert outfit_resp.status_code != 429
