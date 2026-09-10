"""Payment module tests (FR-015, FR-016, BR-001). The Stripe client is
always monkeypatched (fake_stripe fixture below) -- never a real API call,
same posture as ai_recorder for the AI provider (BR-006)."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import stripe
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.facial_analysis_result import FacialAnalysisResult
from app.models.payment import Payment
from app.services.photo_validation_service import REQUIRED_ANGLES
from tests.integration.test_auth_flow import _register_and_verify
from tests.integration.test_questionnaire_flow import _full_valid_answers

pytestmark = pytest.mark.asyncio

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "photos"


def _load(name: str) -> bytes:
    return (FIXTURES_DIR / name).read_bytes()


# Angle-appropriate fixtures for the pose_match check -- see
# test_photo_flow.py's own copy of this map for the full rationale.
_FIXTURE_FOR_ANGLE = {
    "front": "pass_all.jpg",
    "right_3q": "pass_right_3q.jpg",
    "left_3q": "pass_left_3q.jpg",
}


async def _auth_headers(client: AsyncClient, email_sender, email: str) -> dict:
    tokens = await _register_and_verify(client, email_sender, email)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _complete_onboarding(client: AsyncClient, headers: dict) -> None:
    """Questionnaire + photos complete -- exactly the state a real user is
    in right before hitting "Unlock & Start Analysis." No analysis exists
    yet; payment is a prerequisite for analysis to even be triggerable."""
    resp = await client.post(
        "/questionnaire/responses",
        headers=headers,
        json={"answers": _full_valid_answers(), "disclaimer_accepted": True},
    )
    assert resp.status_code == 201, resp.text

    for angle in REQUIRED_ANGLES:
        fixture = _FIXTURE_FOR_ANGLE[angle.id]
        resp = await client.post(
            "/photos",
            headers=headers,
            data={"angle": angle.id, "capture_method": "upload"},
            files={"file": (fixture, _load(fixture), "image/jpeg")},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["validation_status"] == "passed", resp.text


class _FakeStripe:
    """Monkeypatched in place of payment_service.get_stripe_client() --
    never calls the real Stripe API. Records created sessions so tests can
    assert on what was actually sent (price, metadata)."""

    VALID_SIGNATURE = "valid-signature"

    def __init__(self) -> None:
        self.sessions_created: list[dict] = []
        self._next_id = 0

    def _create_session(self, **kwargs: object) -> SimpleNamespace:
        self._next_id += 1
        session_id = f"cs_test_{self._next_id}"
        self.sessions_created.append({"id": session_id, **kwargs})
        return SimpleNamespace(id=session_id, url=f"https://checkout.stripe.com/pay/{session_id}")

    @property
    def checkout(self) -> SimpleNamespace:
        return SimpleNamespace(Session=SimpleNamespace(create=self._create_session))

    def _construct_event(self, payload: bytes, sig_header: str, secret: str | None) -> dict:
        if sig_header != self.VALID_SIGNATURE:
            raise stripe.SignatureVerificationError("Signature verification failed", sig_header)
        return json.loads(payload)

    @property
    def Webhook(self) -> SimpleNamespace:  # noqa: N802 -- matches stripe's own PascalCase attribute
        return SimpleNamespace(construct_event=self._construct_event)


@pytest.fixture
def fake_stripe(monkeypatch) -> _FakeStripe:
    fake = _FakeStripe()
    monkeypatch.setattr("app.services.payment_service.get_stripe_client", lambda: fake)
    return fake


def _completed_event(session_id: str) -> bytes:
    return json.dumps({"type": "checkout.session.completed", "data": {"object": {"id": session_id}}}).encode()


class TestCreateCheckout:
    async def test_requires_authentication(self, client: AsyncClient):
        resp = await client.post("/payments/checkout")
        assert resp.status_code == 401

    async def test_fails_without_completed_questionnaire(
        self, client: AsyncClient, email_sender, fake_stripe: _FakeStripe
    ):
        headers = await _auth_headers(client, email_sender, "pay-no-q@example.com")
        resp = await client.post("/payments/checkout", headers=headers)
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "QUESTIONNAIRE_NOT_SUBMITTED"

    async def test_fails_without_completed_photos(
        self, client: AsyncClient, email_sender, fake_stripe: _FakeStripe
    ):
        headers = await _auth_headers(client, email_sender, "pay-no-photos@example.com")
        resp = await client.post(
            "/questionnaire/responses",
            headers=headers,
            json={"answers": _full_valid_answers(), "disclaimer_accepted": True},
        )
        assert resp.status_code == 201
        resp = await client.post("/payments/checkout", headers=headers)
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "PHOTO_SET_NOT_READY"

    async def test_creates_session_and_payment_row(
        self, client: AsyncClient, email_sender, fake_stripe: _FakeStripe, db: AsyncSession
    ):
        headers = await _auth_headers(client, email_sender, "pay-checkout@example.com")
        await _complete_onboarding(client, headers)

        resp = await client.post("/payments/checkout", headers=headers)
        assert resp.status_code == 200, resp.text
        assert resp.json()["checkout_url"].startswith("https://checkout.stripe.com/")
        assert len(fake_stripe.sessions_created) == 1
        # FR-016/OQ-002: price must come from configuration, never be inlined.
        from app.core.config import get_settings

        settings = get_settings()
        sent = fake_stripe.sessions_created[0]
        assert sent["line_items"][0]["price_data"]["unit_amount"] == settings.report_price_cents

        count = await db.execute(select(func.count()).select_from(Payment))
        assert count.scalar_one() == 1

    async def test_fails_when_a_photo_doesnt_match_the_others(
        self, client: AsyncClient, email_sender, fake_stripe: _FakeStripe
    ):
        """Server-side half of the identity check -- PhotoSetCompleteStep.tsx
        already blocks Continue in the UI, but checkout must independently
        reject it too, same as every other payment guard in this codebase
        (see app.exceptions.PhotoIdentityMismatchError)."""
        headers = await _auth_headers(client, email_sender, "pay-identity-mismatch@example.com")
        resp = await client.post(
            "/questionnaire/responses",
            headers=headers,
            json={"answers": _full_valid_answers(), "disclaimer_accepted": True},
        )
        assert resp.status_code == 201

        resp = await client.post(
            "/photos",
            headers=headers,
            data={"angle": "front", "capture_method": "upload"},
            files={"file": ("different_person.jpg", _load("different_person.jpg"), "image/jpeg")},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["validation_status"] == "passed"
        for angle_id in ("right_3q", "left_3q"):
            fixture = _FIXTURE_FOR_ANGLE[angle_id]
            resp = await client.post(
                "/photos",
                headers=headers,
                data={"angle": angle_id, "capture_method": "upload"},
                files={"file": (fixture, _load(fixture), "image/jpeg")},
            )
            assert resp.status_code == 200, resp.text
            assert resp.json()["validation_status"] == "passed"

        resp = await client.post("/payments/checkout", headers=headers)
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "PHOTO_IDENTITY_MISMATCH"

    async def test_already_paid_is_conflict(
        self, client: AsyncClient, email_sender, fake_stripe: _FakeStripe
    ):
        headers = await _auth_headers(client, email_sender, "pay-already-paid@example.com")
        await _complete_onboarding(client, headers)

        first = await client.post("/payments/checkout", headers=headers)
        session_id = fake_stripe.sessions_created[0]["id"]
        webhook = await client.post(
            "/payments/webhook",
            content=_completed_event(session_id),
            headers={"Stripe-Signature": _FakeStripe.VALID_SIGNATURE},
        )
        assert webhook.status_code == 200

        second = await client.post("/payments/checkout", headers=headers)
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "ALREADY_PAID"
        assert first.status_code == 200  # sanity: first call itself succeeded


class TestPaymentStatus:
    async def test_unpaid_before_any_checkout(self, client: AsyncClient, email_sender):
        headers = await _auth_headers(client, email_sender, "pay-status-none@example.com")
        resp = await client.get("/payments/status", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "unpaid"
        assert body["price_cents"] > 0

    async def test_succeeded_after_webhook(
        self, client: AsyncClient, email_sender, fake_stripe: _FakeStripe
    ):
        headers = await _auth_headers(client, email_sender, "pay-status-paid@example.com")
        await _complete_onboarding(client, headers)
        await client.post("/payments/checkout", headers=headers)
        session_id = fake_stripe.sessions_created[0]["id"]
        await client.post(
            "/payments/webhook",
            content=_completed_event(session_id),
            headers={"Stripe-Signature": _FakeStripe.VALID_SIGNATURE},
        )

        resp = await client.get("/payments/status", headers=headers)
        assert resp.json()["status"] == "succeeded"


class TestWebhook:
    async def test_invalid_signature_is_rejected(self, client: AsyncClient, fake_stripe: _FakeStripe):
        resp = await client.post(
            "/payments/webhook",
            content=_completed_event("cs_test_whatever"),
            headers={"Stripe-Signature": "not-the-real-signature"},
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_WEBHOOK_SIGNATURE"

    async def test_missing_signature_header_is_rejected(self, client: AsyncClient):
        resp = await client.post("/payments/webhook", content=_completed_event("cs_test_whatever"))
        assert resp.status_code == 422  # FastAPI's own required-header validation

    async def test_completed_event_marks_payment_succeeded(
        self, client: AsyncClient, email_sender, fake_stripe: _FakeStripe, db: AsyncSession
    ):
        headers = await _auth_headers(client, email_sender, "pay-webhook@example.com")
        await _complete_onboarding(client, headers)
        await client.post("/payments/checkout", headers=headers)
        session_id = fake_stripe.sessions_created[0]["id"]

        resp = await client.post(
            "/payments/webhook",
            content=_completed_event(session_id),
            headers={"Stripe-Signature": _FakeStripe.VALID_SIGNATURE},
        )
        assert resp.status_code == 200

        result = await db.execute(select(Payment).where(Payment.stripe_session_id == session_id))
        payment = result.scalar_one()
        assert payment.status == "succeeded"

    async def test_completed_event_does_not_auto_trigger_analysis(
        self, client: AsyncClient, email_sender, fake_stripe: _FakeStripe, db: AsyncSession
    ):
        """The webhook only ever flips Payment.status -- the actual
        analysis trigger stays a user-facing "Start Analysis" click on
        POST /analysis (see payment_service.py's module docstring for why:
        auto-triggering made the "analyzing" step invisible when the
        pipeline finished in a couple of seconds)."""
        headers = await _auth_headers(client, email_sender, "pay-notrigger@example.com")
        await _complete_onboarding(client, headers)
        await client.post("/payments/checkout", headers=headers)
        session_id = fake_stripe.sessions_created[0]["id"]

        await client.post(
            "/payments/webhook",
            content=_completed_event(session_id),
            headers={"Stripe-Signature": _FakeStripe.VALID_SIGNATURE},
        )

        status_resp = await client.get("/analysis/status", headers=headers)
        assert status_resp.json()["status"] == "none"

    async def test_unknown_session_id_is_ignored_not_errored(self, client: AsyncClient, fake_stripe: _FakeStripe):
        resp = await client.post(
            "/payments/webhook",
            content=_completed_event("cs_test_never_existed"),
            headers={"Stripe-Signature": _FakeStripe.VALID_SIGNATURE},
        )
        assert resp.status_code == 200  # Stripe expects a 200 even for events we can't act on


class TestBR001BypassAttempt:
    """The literal release-blocking test testing-strategy.md flags: analysis
    must stay impossible to start for an unpaid (or merely "pending")
    account even via a direct authenticated API call, never only hidden in
    the UI."""

    async def test_analysis_stays_locked_without_a_succeeded_payment(
        self, client: AsyncClient, email_sender, fake_stripe: _FakeStripe
    ):
        headers = await _auth_headers(client, email_sender, "pay-bypass@example.com")
        await _complete_onboarding(client, headers)

        # Start (but do not complete) a checkout -- a "pending" Payment row
        # must not be treated as paid.
        await client.post("/payments/checkout", headers=headers)

        resp = await client.post("/analysis", headers=headers)
        assert resp.status_code == 402
        assert resp.json()["error"]["code"] == "PAYMENT_REQUIRED"

    async def test_analysis_unlocks_only_after_webhook_confirms_payment(
        self, client: AsyncClient, email_sender, fake_stripe: _FakeStripe, db: AsyncSession
    ):
        headers = await _auth_headers(client, email_sender, "pay-unlock@example.com")
        await _complete_onboarding(client, headers)
        await client.post("/payments/checkout", headers=headers)
        session_id = fake_stripe.sessions_created[0]["id"]

        await client.post(
            "/payments/webhook",
            content=_completed_event(session_id),
            headers={"Stripe-Signature": _FakeStripe.VALID_SIGNATURE},
        )

        # The webhook itself never creates an analysis row (see TestWebhook
        # above) -- POST /analysis now succeeds because payment succeeded,
        # proving the unlock without the guard itself starting anything.
        trigger = await client.post("/analysis", headers=headers)
        assert trigger.status_code == 200, trigger.text

        result = await db.execute(select(func.count()).select_from(FacialAnalysisResult))
        assert result.scalar_one() == 1


class TestListPayments:
    async def test_requires_authentication(self, client: AsyncClient):
        resp = await client.get("/payments")
        assert resp.status_code == 401

    async def test_lists_only_the_caller_own_payments(
        self, client: AsyncClient, email_sender, fake_stripe: _FakeStripe
    ):
        headers_a = await _auth_headers(client, email_sender, "pay-list-a@example.com")
        await _complete_onboarding(client, headers_a)
        await client.post("/payments/checkout", headers=headers_a)

        headers_b = await _auth_headers(client, email_sender, "pay-list-b@example.com")
        resp = await client.get("/payments", headers=headers_b)
        assert resp.status_code == 200
        assert resp.json() == []

        resp_a = await client.get("/payments", headers=headers_a)
        assert len(resp_a.json()) == 1
