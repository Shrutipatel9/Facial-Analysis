import re
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment
from app.models.report_pdf_blob import ReportPdfBlob
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


def _fake_completion_response() -> SimpleNamespace:
    import json

    content = json.dumps(
        {
            "features": {
                feature: {
                    "narrative": f"Narrative for {feature}.",
                    "summary_callout": feature,
                    "strengths": "Looks natural.",
                    "areas_of_note": "None notable.",
                    "recommendation_ideas": ["Use a daily moisturizer."],
                }
                for feature in ANALYSIS_FEATURES
            },
            "closing_recommendations": "Consider seeing a dermatologist for a full assessment.",
        }
    )
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


@pytest.fixture
def ai_recorder(monkeypatch):
    async def create(**kwargs):
        return _fake_completion_response()

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr("app.services.ai_narrative_service.get_ai_client", lambda: fake_client)


async def _mark_paid(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Simulates a succeeded Stripe payment directly (bypassing Stripe
    entirely) -- see test_payment_flow.py for the actual checkout/webhook
    flow tests."""
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


async def _complete_paid_analysis(client: AsyncClient, headers: dict, db: AsyncSession, user_id: uuid.UUID) -> str:
    """Full pay-before-analysis flow: questionnaire + photos + a succeeded
    payment (simulated directly, not via real Stripe) are all prerequisites
    before POST /analysis will even create a row -- requires the
    ai_recorder fixture also active, since the pipeline now runs CV +
    narrative together in one pass. Returns the analysis id."""
    await _complete_questionnaire(client, headers)
    await _complete_photos(client, headers)
    await _mark_paid(db, user_id)
    trigger = await client.post("/analysis", headers=headers)
    assert trigger.status_code == 200, trigger.text
    analysis_id = trigger.json()["id"]
    await run_analysis_pipeline(uuid.UUID(analysis_id))
    return analysis_id


class TestCreateReport:
    async def test_requires_authentication(self, client: AsyncClient):
        resp = await client.post("/reports")
        assert resp.status_code == 401

    async def test_fails_before_analysis_completes(self, client: AsyncClient, email_sender):
        headers, _ = await _auth_headers_and_user_id(client, email_sender, "rp-no-analysis@example.com")
        resp = await client.post("/reports", headers=headers)
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "ANALYSIS_NOT_COMPLETED"

    async def test_succeeds_after_paid_analysis_completes(
        self, client: AsyncClient, email_sender, ai_recorder, db: AsyncSession
    ):
        """A Report can only ever be created from a completed analysis,
        which itself can only exist after payment succeeded -- so `full`
        is always populated the moment the report exists, no separate
        teaser-only state."""
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "rp-create@example.com")
        await _complete_paid_analysis(client, headers, db, user_id)

        resp = await client.post("/reports", headers=headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["publish_state"] == "published"
        assert set(body["teaser"]["feature_summaries"].keys()) == set(ANALYSIS_FEATURES)
        assert set(body["full"]["features"].keys()) == set(ANALYSIS_FEATURES)
        assert set(body["full"]["recommendations"].keys()) == {"at_home", "otc_skincare", "in_clinic"}
        # Real AI text, since narrative always runs as part of the paid pipeline.
        assert body["teaser"]["feature_summaries"]["hair"] == "hair"

    async def test_second_create_is_idempotent(
        self, client: AsyncClient, email_sender, ai_recorder, db: AsyncSession
    ):
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "rp-idempotent@example.com")
        await _complete_paid_analysis(client, headers, db, user_id)

        first = await client.post("/reports", headers=headers)
        second = await client.post("/reports", headers=headers)
        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["id"] == second.json()["id"]

    async def test_narrative_failure_is_picked_up_on_a_later_read_after_retry(
        self, client: AsyncClient, email_sender, db: AsyncSession, monkeypatch
    ):
        """A narrative-generation failure after payment leaves the analysis
        row "completed" with narrative_result null (see
        analysis_service.run_analysis_pipeline's docstring) -- report
        creation still succeeds, using the templated fallback text. A
        manual re-invoke of the pipeline, once it succeeds, must be picked
        up on the next GET without deleting/recreating the report."""
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "rp-retry@example.com")
        await _complete_questionnaire(client, headers)
        await _complete_photos(client, headers)
        await _mark_paid(db, user_id)

        async def _boom(**kwargs):
            raise RuntimeError("simulated AI failure")

        monkeypatch.setattr(
            "app.services.ai_narrative_service.get_ai_client",
            lambda: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=_boom))),
        )
        trigger = await client.post("/analysis", headers=headers)
        analysis_id = trigger.json()["id"]
        await run_analysis_pipeline(uuid.UUID(analysis_id))

        created = await client.post("/reports", headers=headers)
        report_id = created.json()["id"]
        assert created.json()["full"]["closing_recommendations"] == ""

        # Retry, this time patched to a working client -- overrides the
        # failing one above, monkeypatch doesn't auto-revert mid-test.
        async def _create(**kwargs):
            return _fake_completion_response()

        monkeypatch.setattr(
            "app.services.ai_narrative_service.get_ai_client",
            lambda: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=_create))),
        )
        await run_analysis_pipeline(uuid.UUID(analysis_id))

        resp = await client.get(f"/reports/{report_id}", headers=headers)
        assert resp.json()["full"]["closing_recommendations"] != ""


class TestListAndGetReport:
    async def test_list_is_empty_before_creation(self, client: AsyncClient, email_sender):
        headers, _ = await _auth_headers_and_user_id(client, email_sender, "rp-list-empty@example.com")
        resp = await client.get("/reports", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_and_get_after_creation(
        self, client: AsyncClient, email_sender, ai_recorder, db: AsyncSession
    ):
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "rp-list-get@example.com")
        await _complete_paid_analysis(client, headers, db, user_id)
        created = await client.post("/reports", headers=headers)
        report_id = created.json()["id"]

        listed = await client.get("/reports", headers=headers)
        assert listed.status_code == 200
        assert [row["id"] for row in listed.json()] == [report_id]

        fetched = await client.get(f"/reports/{report_id}", headers=headers)
        assert fetched.status_code == 200
        assert fetched.json()["id"] == report_id

    async def test_unknown_id_is_generic_404(self, client: AsyncClient, email_sender):
        headers, _ = await _auth_headers_and_user_id(client, email_sender, "rp-404@example.com")
        resp = await client.get(f"/reports/{uuid.uuid4()}", headers=headers)
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "REPORT_NOT_FOUND"

    async def test_other_users_report_is_generic_404(
        self, client: AsyncClient, email_sender, ai_recorder, db: AsyncSession
    ):
        headers_a, user_id_a = await _auth_headers_and_user_id(client, email_sender, "rp-owner-a@example.com")
        await _complete_paid_analysis(client, headers_a, db, user_id_a)
        created = await client.post("/reports", headers=headers_a)
        report_id = created.json()["id"]

        headers_b, _ = await _auth_headers_and_user_id(client, email_sender, "rp-owner-b@example.com")
        resp = await client.get(f"/reports/{report_id}", headers=headers_b)
        assert resp.status_code == 404


class TestReportPdf:
    async def test_first_download_generates_and_caches(
        self, client: AsyncClient, email_sender, ai_recorder, db: AsyncSession
    ):
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "rp-pdf@example.com")
        await _complete_paid_analysis(client, headers, db, user_id)
        report_id = (await client.post("/reports", headers=headers)).json()["id"]

        resp = await client.get(f"/reports/{report_id}/pdf", headers=headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content.startswith(b"%PDF")

        blob = await db.get(ReportPdfBlob, f"{report_id}.pdf")
        assert blob is not None

    async def test_second_download_is_served_from_cache(
        self, client: AsyncClient, email_sender, ai_recorder, db: AsyncSession
    ):
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "rp-pdf-cache@example.com")
        await _complete_paid_analysis(client, headers, db, user_id)
        report_id = (await client.post("/reports", headers=headers)).json()["id"]

        first = await client.get(f"/reports/{report_id}/pdf", headers=headers)
        second = await client.get(f"/reports/{report_id}/pdf", headers=headers)
        assert first.content == second.content

        from sqlalchemy import func, select

        count = await db.execute(select(func.count()).select_from(ReportPdfBlob))
        assert count.scalar_one() == 1

    async def test_unknown_report_is_404(self, client: AsyncClient, email_sender):
        headers, _ = await _auth_headers_and_user_id(client, email_sender, "rp-pdf-404@example.com")
        resp = await client.get(f"/reports/{uuid.uuid4()}/pdf", headers=headers)
        assert resp.status_code == 404

    async def test_pdf_is_not_duplicated(
        self, client: AsyncClient, email_sender, ai_recorder, db: AsyncSession
    ):
        """Regression test for a bug where _ReportCanvas finalized every
        page twice (once live, without a footer, once again replayed from
        save() with a footer) -- producing a single PDF file containing two
        full copies of the report merged together. Counts `/Type /Page`
        page objects directly in the raw PDF bytes (no PDF-parsing
        dependency in this project) rather than just checking it opens."""
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "rp-pdf-dup@example.com")
        await _complete_paid_analysis(client, headers, db, user_id)
        report_id = (await client.post("/reports", headers=headers)).json()["id"]

        resp = await client.get(f"/reports/{report_id}/pdf", headers=headers)
        assert resp.status_code == 200

        page_objects = re.findall(rb"/Type\s*/Page[^s]", resp.content)
        expected_pages = 5 + len(ANALYSIS_FEATURES) + 1 + 1  # front matter + features + recommendations + appendix
        assert len(page_objects) == expected_pages

        count_match = re.search(rb"/Count\s+(\d+)", resp.content)
        assert count_match is not None
        assert int(count_match.group(1)) == expected_pages

    async def test_pdf_filename_is_facial_report_with_date(
        self, client: AsyncClient, email_sender, ai_recorder, db: AsyncSession
    ):
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "rp-pdf-filename@example.com")
        await _complete_paid_analysis(client, headers, db, user_id)
        create_resp = await client.post("/reports", headers=headers)
        report_id = create_resp.json()["id"]
        created_date = create_resp.json()["created_at"][:10]

        resp = await client.get(f"/reports/{report_id}/pdf", headers=headers)
        assert resp.status_code == 200
        assert resp.headers["content-disposition"] == f'attachment; filename="facial_report_{created_date}.pdf"'


class TestReportFeatureImage:
    """Feature-crop images are CV-derived, available as soon as the paid
    analysis pipeline completes -- same timing as the rest of the report."""

    async def test_available_feature_returns_jpeg(
        self, client: AsyncClient, email_sender, ai_recorder, db: AsyncSession
    ):
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "rp-img-ok@example.com")
        await _complete_paid_analysis(client, headers, db, user_id)
        report_id = (await client.post("/reports", headers=headers)).json()["id"]

        resp = await client.get(f"/reports/{report_id}/features/eyes/image", headers=headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/jpeg"
        assert resp.content[:2] == b"\xff\xd8"  # JPEG magic bytes

    async def test_unknown_feature_is_404(
        self, client: AsyncClient, email_sender, ai_recorder, db: AsyncSession
    ):
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "rp-img-unknown@example.com")
        await _complete_paid_analysis(client, headers, db, user_id)
        report_id = (await client.post("/reports", headers=headers)).json()["id"]

        resp = await client.get(f"/reports/{report_id}/features/not-a-feature/image", headers=headers)
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "REPORT_IMAGE_NOT_FOUND"

    async def test_unknown_report_is_404(self, client: AsyncClient, email_sender):
        headers, _ = await _auth_headers_and_user_id(client, email_sender, "rp-img-404@example.com")
        resp = await client.get(f"/reports/{uuid.uuid4()}/features/eyes/image", headers=headers)
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "REPORT_NOT_FOUND"
