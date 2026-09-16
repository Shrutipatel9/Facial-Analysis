import asyncio
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment
from app.services.ai_narrative_service import _FEATURE_SUBSECTIONS
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
                    "sections": {heading: f"{heading} for {feature}." for heading in _FEATURE_SUBSECTIONS[feature]},
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

    async def test_fails_when_a_photo_doesnt_match_the_others(
        self, client: AsyncClient, email_sender, db: AsyncSession
    ):
        """Server-side half of the identity check -- redundant with
        payments.checkout's own guard (defense in depth, same posture as
        this same function's is_photo_set_ready/payment re-checks) in case
        analysis is ever triggered through a path that didn't go through
        checkout."""
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "an-identity-mismatch@example.com")
        await _complete_questionnaire(client, headers)

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

        await _mark_paid(db, user_id)
        resp = await client.post("/analysis", headers=headers)
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "PHOTO_IDENTITY_MISMATCH"

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

    async def test_record_is_committed_before_the_background_task_is_scheduled(
        self, client: AsyncClient, email_sender, db: AsyncSession, monkeypatch
    ):
        """Regression test for a real production bug: run_analysis_pipeline
        opens its OWN DB session (module docstring), independent of the
        request's session. trigger_analysis used to only flush() the new
        row before calling schedule_background_task(), not commit() --
        under READ COMMITTED, a flushed-but-uncommitted row is invisible to
        any other session/connection. Because asyncio.create_task() doesn't
        run synchronously, and there are real await points between
        scheduling and the request's get_db-dependency commit (response
        serialization, security-headers/CORS/rate-limit middleware), the
        background task could start and query for the row before it was
        durably committed -- logging "analysis <id> not found" and leaving
        the row stuck on "processing" forever (trigger_analysis's own
        existing-analysis guard only allows a retry once status is
        "failed", so a user who hit this had no in-app recovery path).

        Can't test this by checking row visibility after the HTTP call
        returns -- by then get_db's own teardown commit has already run
        regardless of what trigger_analysis itself did, so a buggy
        flush-only version would pass that check too. This instead spies
        on call *order*: db.commit() must happen before
        schedule_background_task(), which is the actual fix. The spy is
        installed only right before calling trigger_analysis itself (not
        earlier) -- _mark_paid below does its own unrelated db.commit() to
        persist the Payment row, which would otherwise pre-satisfy
        commit_was_called and let this test pass even without the fix."""
        from app.services import analysis_service

        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "an-race@example.com")
        await _complete_questionnaire(client, headers)
        await _complete_photos(client, headers)
        await _mark_paid(db, user_id)

        commit_was_called = False
        commit_called_before_schedule = False
        original_commit = db.commit

        async def spy_commit():
            nonlocal commit_was_called
            commit_was_called = True
            await original_commit()

        def spy_schedule(coro):
            nonlocal commit_called_before_schedule
            commit_called_before_schedule = commit_was_called
            coro.close()  # never actually run the real pipeline in this test

        monkeypatch.setattr(db, "commit", spy_commit)
        monkeypatch.setattr(analysis_service, "schedule_background_task", spy_schedule)

        # Calls trigger_analysis directly against this test's own `db`
        # session (not via the HTTP client, whose request gets FastAPI's
        # own separately-injected session that this test can't monkeypatch)
        # -- the same service function the endpoint itself calls.
        await analysis_service.trigger_analysis(db, user_id)

        assert commit_was_called, "trigger_analysis must commit the new analysis row"
        assert commit_called_before_schedule, "commit() must happen before schedule_background_task()"

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

        monkeypatch.setattr("app.services.analysis_service.extract_measurements_and_assessments", _boom)

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

        monkeypatch.setattr("app.services.analysis_service.extract_measurements_and_assessments", _boom)

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

    async def test_completion_auto_starts_ai_visuals_when_image_gen_is_configured(
        self, client: AsyncClient, email_sender, ai_recorder: _Recorder, db: AsyncSession, monkeypatch
    ):
        """2026-09-17, user-reported: AI Visuals used to only ever start
        generating on the user's first /ai-visuals page visit, which could
        show a fresh error/pending state right when they landed on it.
        Analysis completion now auto-starts all 3 kinds itself -- gated on
        image_gen_api_key being configured (see analysis_service.py's
        comment) since tests deliberately leave it blank (BR-006)."""
        from app.core.config import get_settings

        monkeypatch.setenv("IMAGE_GEN_API_KEY", "test-key-for-this-assertion-only")
        get_settings.cache_clear()

        calls: list[tuple[uuid.UUID, str]] = []

        async def _fake_get_or_create_visuals(db_arg, user_id, kind):  # noqa: ARG001 -- db unused, matches real signature
            calls.append((user_id, kind))
            return []

        monkeypatch.setattr(
            "app.services.ai_visual_service.get_or_create_visuals",
            _fake_get_or_create_visuals,
        )

        try:
            headers, user_id = await _auth_headers_and_user_id(client, email_sender, "an-visuals-autostart@example.com")
            await _complete_questionnaire(client, headers)
            await _complete_photos(client, headers)
            await _mark_paid(db, user_id)
            trigger = await client.post("/analysis", headers=headers)
            await run_analysis_pipeline(uuid.UUID(trigger.json()["id"]))
        finally:
            get_settings.cache_clear()

        assert {kind for _, kind in calls} == {"hairstyle", "outfit", "aging", "potential"}
        assert all(called_user_id == user_id for called_user_id, _ in calls)

    async def test_completion_does_not_auto_start_ai_visuals_without_a_configured_key(
        self, client: AsyncClient, email_sender, ai_recorder: _Recorder, db: AsyncSession, monkeypatch
    ):
        """Companion to the auto-start test above: with no image-gen key
        configured (this project's normal test posture, and a legitimate
        ops state in production), completion must not create AiVisual rows
        or schedule generation for every analysis -- see the key-presence
        guard's own comment in analysis_service.py for why."""
        calls: list[tuple[uuid.UUID, str]] = []

        async def _fake_get_or_create_visuals(db_arg, user_id, kind):  # noqa: ARG001
            calls.append((user_id, kind))
            return []

        monkeypatch.setattr(
            "app.services.ai_visual_service.get_or_create_visuals",
            _fake_get_or_create_visuals,
        )

        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "an-visuals-no-key@example.com")
        await _complete_questionnaire(client, headers)
        await _complete_photos(client, headers)
        await _mark_paid(db, user_id)
        trigger = await client.post("/analysis", headers=headers)
        await run_analysis_pipeline(uuid.UUID(trigger.json()["id"]))

        assert calls == []


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
