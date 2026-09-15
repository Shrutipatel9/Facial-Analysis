import asyncio
import re
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.facial_analysis_result import FacialAnalysisResult
from app.models.payment import Payment
from app.models.report import Report
from app.models.report_feature_visual import ReportFeatureVisual
from app.models.report_pdf_blob import ReportPdfBlob
from app.services.analysis_service import run_analysis_pipeline
from app.services.facial_assessment_service import ASSESSMENT_CATEGORIES
from app.services.facial_measurement_service import ANALYSIS_FEATURES
from app.services.photo_validation_service import REQUIRED_ANGLES
from app.services.report_pdf_service import _FRONT_MATTER_PAGE_COUNT
from tests.conftest import _fake_completion_response
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


# _fake_completion_response / ai_recorder moved to tests/conftest.py once a
# second file (test_ai_visuals_flow.py) needed the exact same fake AI
# client -- a conftest fixture is resolved by name project-wide with no
# import, avoiding the ruff F811 churn re-importing a fixture into another
# test module by name would otherwise cause.


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

    async def test_stale_cache_is_re_rendered_in_place(
        self, client: AsyncClient, email_sender, ai_recorder, db: AsyncSession
    ):
        """Regression test: a feature visual completing *after* the cached
        PDF was rendered must trigger a re-render (see
        report_service._has_visual_newer_than) that UPDATEs the existing
        ReportPdfBlob row rather than INSERTing a second row under the same
        `f"{report_id}.pdf"` primary key -- the naive fix originally raised
        a UniqueViolationError on every stale-cache re-render."""
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "rp-pdf-stale@example.com")
        await _complete_paid_analysis(client, headers, db, user_id)
        report_id = (await client.post("/reports", headers=headers)).json()["id"]

        first = await client.get(f"/reports/{report_id}/pdf", headers=headers)
        assert first.status_code == 200
        first_blob = await db.get(ReportPdfBlob, f"{report_id}.pdf")
        assert first_blob is not None

        # Simulate a feature visual completing after the cached render.
        result = await db.execute(
            select(ReportFeatureVisual).where(ReportFeatureVisual.report_id == report_id).limit(1)
        )
        visual = result.scalar_one()
        visual.status = "generated"
        visual.content = _load("pass_all.jpg")  # real decodable image -- render_pdf feeds it through PIL
        visual.content_type = "image/jpeg"
        await db.commit()

        second = await client.get(f"/reports/{report_id}/pdf", headers=headers)
        assert second.status_code == 200
        assert second.content.startswith(b"%PDF")

        from sqlalchemy import func

        count = await db.execute(select(func.count()).select_from(ReportPdfBlob))
        assert count.scalar_one() == 1

    async def test_pdf_reference_reset_reuses_existing_blob_row(
        self, client: AsyncClient, email_sender, ai_recorder, db: AsyncSession
    ):
        """Regression test: _sync_sections resets Report.pdf_reference to
        None to force a narrative-driven re-render (report_service.py's
        module docstring) without deleting the now-orphaned ReportPdfBlob
        row that still sits under the same deterministic `f"{report_id}.pdf"`
        id. A subsequent download must still update that row in place, not
        blindly INSERT under the same already-occupied primary key."""
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "rp-pdf-ref-reset@example.com")
        await _complete_paid_analysis(client, headers, db, user_id)
        report_id = (await client.post("/reports", headers=headers)).json()["id"]

        first = await client.get(f"/reports/{report_id}/pdf", headers=headers)
        assert first.status_code == 200

        # Simulate _sync_sections' narrative-driven invalidation: the
        # pointer is cleared, but the blob row itself is untouched.
        report = await db.get(Report, uuid.UUID(report_id))
        assert report is not None
        report.pdf_reference = None
        await db.commit()

        second = await client.get(f"/reports/{report_id}/pdf", headers=headers)
        assert second.status_code == 200
        assert second.content.startswith(b"%PDF")

        from sqlalchemy import func

        count = await db.execute(select(func.count()).select_from(ReportPdfBlob))
        assert count.scalar_one() == 1

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
        # front matter (imported from report_pdf_service.py so this test
        # actually stays in sync when front matter grows, rather than
        # silently drifting the way a hardcoded number did before) +
        # features (every one of the 11 always starts its own fresh page,
        # per explicit client instruction -- no shared pages) +
        # recommendations + appendix
        expected_pages = _FRONT_MATTER_PAGE_COUNT + len(ANALYSIS_FEATURES) + 1 + 1
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


class TestFacialAssessmentsInReport:
    """Milestone 2 (FR-018) -- the fields report_assembly_service.py adds
    to `sections`, surfaced through GET /reports/{id}."""

    async def test_full_content_includes_all_new_fields(
        self, client: AsyncClient, email_sender, ai_recorder, db: AsyncSession
    ):
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "rp-assess-ok@example.com")
        await _complete_paid_analysis(client, headers, db, user_id)
        resp = await client.post("/reports", headers=headers)
        assert resp.status_code == 200, resp.text
        full = resp.json()["full"]

        assert set(full["facial_assessments"].keys()) == set(ASSESSMENT_CATEGORIES)
        assert set(full["feature_scores"].keys()) == set(ANALYSIS_FEATURES)
        assert "overall_score" in full
        assert set(full["harmony_chart"].keys()) == {
            "harmony",
            "symmetry",
            "smoothness",
            "jawline",
            "skin",
            "volume",
        }
        # A real analyzed photo (pass_all.jpg) should produce available
        # assessments, not an all-unavailable placeholder.
        assert full["facial_assessments"]["dimorphism"]["available"] is True

    async def test_analysis_duration_is_a_real_positive_elapsed_time(
        self, client: AsyncClient, email_sender, ai_recorder, db: AsyncSession
    ):
        """Dashboard consolidation -- FacialAnalysisResult.completed_at -
        created_at, not a fabricated value. A completed analysis always has
        both timestamps set, so this must be a real positive number, not
        null, once run_analysis_pipeline has actually finished."""
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "rp-duration@example.com")
        await _complete_paid_analysis(client, headers, db, user_id)
        resp = await client.post("/reports", headers=headers)
        assert resp.status_code == 200, resp.text
        full = resp.json()["full"]

        assert full["analysis_duration_seconds"] is not None
        assert full["analysis_duration_seconds"] >= 0

    async def test_every_feature_section_has_a_visual_status(
        self, client: AsyncClient, email_sender, ai_recorder, db: AsyncSession
    ):
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "rp-assess-visual@example.com")
        await _complete_paid_analysis(client, headers, db, user_id)
        resp = await client.post("/reports", headers=headers)
        features = resp.json()["full"]["features"]
        for feature in ANALYSIS_FEATURES:
            assert features[feature]["visual_status"] in (
                "not_attempted",
                "pending",
                "generating",
                "generated",
                "failed",
            )


class TestLegacyReportRegression:
    """A report assembled from a FacialAnalysisResult with
    facial_assessments=None (i.e. created before this migration existed)
    must still return a fully-shaped, all-unavailable Milestone 2 section
    -- additive-only, per milestone2_phase_plan.md's Phase 10 acceptance
    criterion -- never a missing key or a 500."""

    async def test_null_facial_assessments_still_returns_valid_shape(
        self, client: AsyncClient, email_sender, ai_recorder, db: AsyncSession
    ):
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "rp-legacy@example.com")
        await _complete_paid_analysis(client, headers, db, user_id)

        # Simulate a pre-Milestone-2 row directly -- run_analysis_pipeline
        # always populates facial_assessments now, so force it back to
        # None to exercise the legacy path.
        result = await db.execute(select_analysis_result(user_id))
        analysis = result.scalar_one()
        analysis.facial_assessments = None
        await db.commit()

        resp = await client.post("/reports", headers=headers)
        assert resp.status_code == 200, resp.text
        full = resp.json()["full"]
        assert set(full["facial_assessments"].keys()) == set(ASSESSMENT_CATEGORIES)
        assert all(not entry["available"] for entry in full["facial_assessments"].values())

    async def test_zero_visual_rows_reports_not_attempted_for_every_feature(
        self, client: AsyncClient, email_sender, ai_recorder, db: AsyncSession
    ):
        """Simulates a report created before FR-022 existed (no
        ReportFeatureVisual rows at all) -- GET /reports/{id}/visuals/status
        must still return all 11 keys, never a partial dict."""
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "rp-legacy-visuals@example.com")
        await _complete_paid_analysis(client, headers, db, user_id)
        report_id = (await client.post("/reports", headers=headers)).json()["id"]

        # Delete the rows report creation just inserted, simulating a
        # report that predates FR-022.
        result = await db.execute(select_report_visuals(uuid.UUID(report_id)))
        for row in result.scalars().all():
            await db.delete(row)
        await db.commit()

        resp = await client.get(f"/reports/{report_id}/visuals/status", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert set(body.keys()) == set(ANALYSIS_FEATURES)
        assert all(status == "not_attempted" for status in body.values())


def select_analysis_result(user_id: uuid.UUID):
    return (
        select(FacialAnalysisResult)
        .where(FacialAnalysisResult.user_id == user_id)
        .order_by(FacialAnalysisResult.created_at.desc())
        .limit(1)
    )


def select_report_visuals(report_id: uuid.UUID):
    return select(ReportFeatureVisual).where(ReportFeatureVisual.report_id == str(report_id))


_TERMINAL_VISUAL_STATUSES = {"generated", "failed"}


async def _wait_for_all_visuals_terminal(db: AsyncSession, report_id: uuid.UUID, timeout: float = 3.0) -> None:
    """Polls until every ReportFeatureVisual row for this report has left
    pending/generating, instead of a fixed sleep -- a fixed-duration sleep
    races the background generation task under system load (11 features
    each need their own async db.commit(), and a slow test run can miss a
    200ms window), which made test_generation_is_triggered_exactly_once_per_report
    flaky."""
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        # populate_existing: rows for this report_id are already in this
        # session's identity map from the previous poll iteration -- a
        # plain select() would keep returning those cached (stale) ORM
        # instances instead of refreshing them from the background task's
        # committed writes.
        result = await db.execute(select_report_visuals(report_id).execution_options(populate_existing=True))
        rows = result.scalars().all()
        if len(rows) == len(ANALYSIS_FEATURES) and all(row.status in _TERMINAL_VISUAL_STATUSES for row in rows):
            return
        await asyncio.sleep(0.05)
    raise AssertionError(f"visual generation did not settle within {timeout}s for report {report_id}")


class TestReportFeatureVisual:
    """Milestone 2 (FR-022). No real Gemini key is configured in tests
    (BR-006 -- real calls never run in CI), so generation always ends in
    "failed" here; these tests cover the endpoint contract, not real
    generation quality."""

    async def test_visuals_status_has_all_eleven_features(
        self, client: AsyncClient, email_sender, ai_recorder, db: AsyncSession
    ):
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "rp-visual-status@example.com")
        await _complete_paid_analysis(client, headers, db, user_id)
        report_id = (await client.post("/reports", headers=headers)).json()["id"]
        await asyncio.sleep(0.2)  # let the background generation task settle (fails fast: no API key configured)

        resp = await client.get(f"/reports/{report_id}/visuals/status", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert set(body.keys()) == set(ANALYSIS_FEATURES)

    async def test_ungenerated_visual_is_404(
        self, client: AsyncClient, email_sender, ai_recorder, db: AsyncSession
    ):
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "rp-visual-404@example.com")
        await _complete_paid_analysis(client, headers, db, user_id)
        report_id = (await client.post("/reports", headers=headers)).json()["id"]
        await asyncio.sleep(0.2)

        resp = await client.get(f"/reports/{report_id}/features/eyes/visual", headers=headers)
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "REPORT_VISUAL_NOT_FOUND"

    async def test_generation_is_triggered_exactly_once_per_report(
        self, client: AsyncClient, email_sender, ai_recorder, db: AsyncSession
    ):
        """BR-006 cost control: a repeat POST /reports (idempotent,
        get-or-create) must not re-insert or reset the visual rows."""
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "rp-visual-once@example.com")
        await _complete_paid_analysis(client, headers, db, user_id)
        report_id = (await client.post("/reports", headers=headers)).json()["id"]
        await _wait_for_all_visuals_terminal(db, uuid.UUID(report_id))

        first = await db.execute(select_report_visuals(uuid.UUID(report_id)))
        first_rows = {row.feature: row.attempt_count for row in first.scalars().all()}
        assert len(first_rows) == len(ANALYSIS_FEATURES)

        await client.post("/reports", headers=headers)  # repeat, idempotent
        await asyncio.sleep(0.05)

        second = await db.execute(select_report_visuals(uuid.UUID(report_id)))
        second_rows = {row.feature: row.attempt_count for row in second.scalars().all()}
        assert second_rows == first_rows  # unchanged -- no re-trigger, no duplicate rows

    async def test_unknown_report_is_404(self, client: AsyncClient, email_sender):
        headers, _ = await _auth_headers_and_user_id(client, email_sender, "rp-visual-unknown-report@example.com")
        resp = await client.get(f"/reports/{uuid.uuid4()}/features/eyes/visual", headers=headers)
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "REPORT_NOT_FOUND"
