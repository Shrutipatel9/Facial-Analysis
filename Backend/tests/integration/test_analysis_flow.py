import asyncio
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment
from app.services.analysis_service import run_analysis_pipeline
from app.services.facial_measurement_service import ANALYSIS_FEATURES
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


async def _auth_headers_and_user_id(client: AsyncClient, email_sender, email: str) -> tuple[dict, uuid.UUID]:
    tokens = await _register_and_verify(client, email_sender, email)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    user_id = uuid.UUID((await client.get("/auth/me", headers=headers)).json()["id"])
    return headers, user_id


async def _complete_questionnaire(client: AsyncClient, headers: dict) -> None:
    resp = await client.post(
        "/questionnaire/responses",
        headers=headers,
        json={"answers": _full_valid_answers(), "disclaimer_accepted": True},
    )
    assert resp.status_code == 201, resp.text


async def _complete_photos(client: AsyncClient, headers: dict) -> None:
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


async def _mark_paid(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Simulates a succeeded Stripe payment directly (bypassing Stripe
    entirely) -- see test_payment_flow.py for the real checkout/webhook
    flow tests, including the auto-trigger-on-webhook behavior."""
    db.add(
        Payment(
            user_id=user_id,
            stripe_session_id=f"cs_test_{uuid.uuid4().hex}",
            status="succeeded",
            amount_cents=1999,
            currency="usd",
        )
    )
    await db.commit()


def _fake_completion_response() -> SimpleNamespace:
    import json

    content = json.dumps(
        {
            "features": {
                feature: {
                    "narrative": f"Narrative for {feature}.",
                    "summary_callout": feature,
                    "recommendation_ideas": ["idea one"],
                }
                for feature in ANALYSIS_FEATURES
            },
            "closing_recommendations": "Overall closing recommendations.",
        }
    )
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


class _Recorder:
    def __init__(self) -> None:
        self.last_kwargs: dict | None = None
        self.should_fail = False


def _build_fake_ai_client(recorder: _Recorder) -> SimpleNamespace:
    async def create(**kwargs):
        recorder.last_kwargs = kwargs
        if recorder.should_fail:
            raise RuntimeError("simulated AI failure")
        return _fake_completion_response()

    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


@pytest.fixture
def ai_recorder(monkeypatch) -> _Recorder:
    recorder = _Recorder()
    fake_client = _build_fake_ai_client(recorder)
    monkeypatch.setattr("app.services.ai_narrative_service.get_ai_client", lambda: fake_client)
    return recorder


class TestTriggerAnalysis:
    async def test_requires_authentication(self, client: AsyncClient):
        resp = await client.post("/analysis")
        assert resp.status_code == 401

    async def test_fails_without_completed_questionnaire(self, client: AsyncClient, email_sender):
        headers, _ = await _auth_headers_and_user_id(client, email_sender, "an-no-q@example.com")
        resp = await client.post("/analysis", headers=headers)
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "QUESTIONNAIRE_NOT_SUBMITTED"

    async def test_fails_without_completed_photos(self, client: AsyncClient, email_sender):
        headers, _ = await _auth_headers_and_user_id(client, email_sender, "an-no-photos@example.com")
        await _complete_questionnaire(client, headers)
        resp = await client.post("/analysis", headers=headers)
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "PHOTO_SET_NOT_READY"

    async def test_fails_without_payment(self, client: AsyncClient, email_sender):
        """The literal BR-001 "payment before analysis start" bypass-attempt
        test -- a direct authenticated API call with questionnaire and
        photos both complete, but no succeeded payment, must still be
        rejected. Release-blocking, same severity as auth's reuse-detection
        test."""
        headers, _ = await _auth_headers_and_user_id(client, email_sender, "an-no-payment@example.com")
        await _complete_questionnaire(client, headers)
        await _complete_photos(client, headers)
        resp = await client.post("/analysis", headers=headers)
        assert resp.status_code == 402
        assert resp.json()["error"]["code"] == "PAYMENT_REQUIRED"

    async def test_succeeds_and_returns_processing_once_paid(
        self, client: AsyncClient, email_sender, db: AsyncSession
    ):
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "an-trigger@example.com")
        await _complete_questionnaire(client, headers)
        await _complete_photos(client, headers)
        await _mark_paid(db, user_id)
        resp = await client.post("/analysis", headers=headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "processing"
        assert body["id"]

    async def test_second_trigger_is_conflict(self, client: AsyncClient, email_sender, db: AsyncSession):
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "an-dup@example.com")
        await _complete_questionnaire(client, headers)
        await _complete_photos(client, headers)
        await _mark_paid(db, user_id)
        first = await client.post("/analysis", headers=headers)
        assert first.status_code == 200
        second = await client.post("/analysis", headers=headers)
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "ANALYSIS_ALREADY_EXISTS"


class TestAnalysisPipeline:
    """CV measurements and the DeepSeek narrative call now run together in
    one pass, only ever after payment has already succeeded (see
    analysis_service.trigger_analysis's guard) -- see
    D:\\zzz\\payment\\plans.md for the pay-before-analysis rationale."""

    async def test_pipeline_produces_measurements_and_narrative_using_both_inputs(
        self, client: AsyncClient, email_sender, ai_recorder: _Recorder, db: AsyncSession
    ):
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "an-pipeline@example.com")
        await _complete_questionnaire(client, headers)
        await _complete_photos(client, headers)
        await _mark_paid(db, user_id)
        trigger = await client.post("/analysis", headers=headers)
        analysis_id = trigger.json()["id"]

        # Awaited directly (not via the detached asyncio.create_task the
        # endpoint itself schedules) so the test stays deterministic.
        await run_analysis_pipeline(uuid.UUID(analysis_id))

        resp = await client.get(f"/analysis/{analysis_id}", headers=headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "completed"
        assert set(body["measurements"].keys()) == set(ANALYSIS_FEATURES)
        assert set(body["narrative_result"]["features"].keys()) == set(ANALYSIS_FEATURES)

        # testing-strategy.md's literal requirement: both measurements AND
        # questionnaire answers must be present in the AI request, not just one.
        assert ai_recorder.last_kwargs is not None
        sent_content = ai_recorder.last_kwargs["messages"][1]["content"][0]["text"]
        assert "eyebrows" in sent_content
        assert "Entrepreneur" in sent_content  # q1 answer from _full_valid_answers()

    async def test_status_stays_processing_until_narrative_call_finishes(
        self, client: AsyncClient, email_sender, monkeypatch, db: AsyncSession
    ):
        """Regression test: `status` must not flip to "completed" right
        after the (fast) CV step while the (slow) DeepSeek call is still in
        flight -- the frontend polls GET /analysis/status and treats
        "completed" as "safe to move on and generate the report." An early
        flip meant the report got assembled from a still-empty
        narrative_result (only images/templated placeholders showing) until
        a later reload happened to pick up the real content."""
        release_narrative_call = asyncio.Event()

        async def _slow_create(**kwargs):
            await release_narrative_call.wait()
            return _fake_completion_response()

        monkeypatch.setattr(
            "app.services.ai_narrative_service.get_ai_client",
            lambda: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=_slow_create))),
        )

        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "an-status-timing@example.com")
        await _complete_questionnaire(client, headers)
        await _complete_photos(client, headers)
        await _mark_paid(db, user_id)
        trigger = await client.post("/analysis", headers=headers)
        analysis_id = trigger.json()["id"]

        pipeline_task = asyncio.create_task(run_analysis_pipeline(uuid.UUID(analysis_id)))
        try:
            # Give the CV step (fast, no external call) time to finish and
            # commit while the narrative call sits blocked on the event.
            for _ in range(20):
                await asyncio.sleep(0.05)
                resp = await client.get(f"/analysis/{analysis_id}", headers=headers)
                body = resp.json()
                if body["measurements"]["hair"] is not None:
                    break
            assert body["status"] == "processing", "status flipped to completed before the narrative call finished"
        finally:
            release_narrative_call.set()
            await pipeline_task

        resp = await client.get(f"/analysis/{analysis_id}", headers=headers)
        body = resp.json()
        assert body["status"] == "completed"
        assert body["narrative_result"] is not None

    async def test_cv_failure_marks_row_failed(
        self, client: AsyncClient, email_sender, monkeypatch, db: AsyncSession
    ):
        def _boom(photos):
            raise RuntimeError("simulated CV failure")

        monkeypatch.setattr("app.services.analysis_service.extract_measurements", _boom)

        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "an-cv-fail@example.com")
        await _complete_questionnaire(client, headers)
        await _complete_photos(client, headers)
        await _mark_paid(db, user_id)
        trigger = await client.post("/analysis", headers=headers)
        analysis_id = trigger.json()["id"]

        await run_analysis_pipeline(uuid.UUID(analysis_id))

        resp = await client.get(f"/analysis/{analysis_id}", headers=headers)
        body = resp.json()
        assert body["status"] == "failed"
        assert body["error_message"]

    async def test_retriggering_after_cv_failure_is_allowed_without_paying_again(
        self, client: AsyncClient, email_sender, monkeypatch, db: AsyncSession
    ):
        def _boom(photos):
            raise RuntimeError("simulated CV failure")

        monkeypatch.setattr("app.services.analysis_service.extract_measurements", _boom)

        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "an-retry@example.com")
        await _complete_questionnaire(client, headers)
        await _complete_photos(client, headers)
        await _mark_paid(db, user_id)
        first = await client.post("/analysis", headers=headers)
        await run_analysis_pipeline(uuid.UUID(first.json()["id"]))

        second = await client.post("/analysis", headers=headers)
        assert second.status_code == 200, second.text

    async def test_narrative_failure_leaves_it_null_without_failing_the_row(
        self, client: AsyncClient, email_sender, ai_recorder: _Recorder, db: AsyncSession
    ):
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "an-narrative-fail@example.com")
        await _complete_questionnaire(client, headers)
        await _complete_photos(client, headers)
        await _mark_paid(db, user_id)
        ai_recorder.should_fail = True
        trigger = await client.post("/analysis", headers=headers)
        analysis_id = trigger.json()["id"]

        await run_analysis_pipeline(uuid.UUID(analysis_id))

        resp = await client.get(f"/analysis/{analysis_id}", headers=headers)
        body = resp.json()
        # CV measurements succeeded and the row is "completed" -- the user
        # already paid and has valid measurements; only the narrative is
        # missing (see D:\zzz\payment\plans.md's open items).
        assert body["status"] == "completed"
        assert body["narrative_result"] is None


class TestAnalysisStatus:
    async def test_none_before_trigger(self, client: AsyncClient, email_sender):
        headers, _ = await _auth_headers_and_user_id(client, email_sender, "an-status-none@example.com")
        resp = await client.get("/analysis/status", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == {"status": "none", "analysis_id": None}

    async def test_processing_then_completed(self, client: AsyncClient, email_sender, db: AsyncSession):
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "an-status-flow@example.com")
        await _complete_questionnaire(client, headers)
        await _complete_photos(client, headers)
        await _mark_paid(db, user_id)
        trigger = await client.post("/analysis", headers=headers)
        analysis_id = trigger.json()["id"]

        resp = await client.get("/analysis/status", headers=headers)
        assert resp.json() == {"status": "processing", "analysis_id": analysis_id}

        await run_analysis_pipeline(uuid.UUID(analysis_id))

        resp = await client.get("/analysis/status", headers=headers)
        assert resp.json() == {"status": "completed", "analysis_id": analysis_id}


class TestGetAnalysis:
    async def test_requires_authentication(self, client: AsyncClient):
        resp = await client.get(f"/analysis/{uuid.uuid4()}")
        assert resp.status_code == 401

    async def test_unknown_id_is_generic_404(self, client: AsyncClient, email_sender):
        headers, _ = await _auth_headers_and_user_id(client, email_sender, "an-404@example.com")
        resp = await client.get(f"/analysis/{uuid.uuid4()}", headers=headers)
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "ANALYSIS_NOT_FOUND"

    async def test_other_users_analysis_is_generic_404(self, client: AsyncClient, email_sender, db: AsyncSession):
        headers_a, user_id_a = await _auth_headers_and_user_id(client, email_sender, "an-owner-a@example.com")
        await _complete_questionnaire(client, headers_a)
        await _complete_photos(client, headers_a)
        await _mark_paid(db, user_id_a)
        trigger = await client.post("/analysis", headers=headers_a)
        analysis_id = trigger.json()["id"]

        headers_b, _ = await _auth_headers_and_user_id(client, email_sender, "an-owner-b@example.com")
        resp = await client.get(f"/analysis/{analysis_id}", headers=headers_b)
        assert resp.status_code == 404
