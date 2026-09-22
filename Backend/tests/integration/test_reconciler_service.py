"""Integration tests for the crash-recovery reconciler (Milestone 3.1,
Phase 21 -- production hardening). Every scenario is covered through this
project's existing mocked-AI-client pattern -- ai_recorder (conftest.py)
for narrative generation, a small local FakeImageClient for image
generation -- so nothing here ever makes a real, billed API call, matching
BR-006 and this project's "never spend real tokens in automated tests"
posture.

Simulates a crash-orphaned row by directly mutating a row's status/
updated_at via the `db` fixture after a normal flow already completed --
this is simpler and more deterministic than trying to actually interrupt a
background task mid-flight, and exercises exactly the same reconciler code
path a real crash would."""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_visual import AiVisual
from app.models.facial_analysis_result import FacialAnalysisResult
from app.models.report_feature_visual import ReportFeatureVisual
from app.services import ai_visual_service, reconciler_service
from app.services.analysis_service import resume_analysis_pipeline
from app.services.facial_measurement_service import ANALYSIS_FEATURES
from tests.integration.test_report_flow import (
    _auth_headers_and_user_id,
    _complete_paid_analysis,
    _complete_photos,
    _complete_questionnaire,
    _mark_paid,
)

pytestmark = pytest.mark.asyncio

# Comfortably past/within reconciler_stuck_threshold_minutes (default 20).
_STALE = timedelta(minutes=30)
_FRESH = timedelta(minutes=1)


async def _settle_stray_background_tasks() -> None:
    """POST /analysis's own trigger_analysis schedules run_analysis_pipeline
    as a background task -- _complete_paid_analysis (test_report_flow.py)
    ALSO awaits run_analysis_pipeline directly, so by the time it returns
    the analysis is already genuinely "completed" either way, but that
    redundant auto-scheduled task can still be independently in flight and
    land its own ai_recorder call slightly later. A brief yield here (well
    over what a mocked, non-network call needs) lets it settle before a
    test captures an ai_recorder.call_count baseline -- without this,
    baseline capture races that straggler task and flakes."""
    await asyncio.sleep(0.1)


class FakeImageClient:
    """Records every prompt it's asked to render -- lets a test assert
    exactly which features triggered a real generation attempt, which no
    real (keyless) image-gen client can do in this test suite."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def generate_before_after(self, *, source_image: bytes, prompt: str) -> bytes:
        self.calls.append(prompt)
        return b"fake-image-bytes"


async def _refetch_analysis(db: AsyncSession, analysis_id: uuid.UUID) -> FacialAnalysisResult:
    result = await db.execute(
        select(FacialAnalysisResult)
        .where(FacialAnalysisResult.id == analysis_id)
        .execution_options(populate_existing=True)
    )
    return result.scalar_one()


async def _wait_for_analysis_status(
    db: AsyncSession, analysis_id: uuid.UUID, status: str, timeout: float = 3.0
) -> None:
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        record = await _refetch_analysis(db, analysis_id)
        if record.status == status:
            return
        await asyncio.sleep(0.05)
    raise AssertionError(f"analysis {analysis_id} did not reach status={status!r} within {timeout}s")


def _select_ai_visuals(user_id: uuid.UUID, kind: str):
    return select(AiVisual).where(AiVisual.user_id == user_id, AiVisual.kind == kind)


async def _wait_for_ai_visuals_terminal(db: AsyncSession, user_id: uuid.UUID, kind: str, timeout: float = 3.0) -> None:
    deadline = asyncio.get_event_loop().time() + timeout
    terminal = {"generated", "failed"}
    while asyncio.get_event_loop().time() < deadline:
        result = await db.execute(_select_ai_visuals(user_id, kind).execution_options(populate_existing=True))
        rows = result.scalars().all()
        if rows and all(row.status in terminal for row in rows):
            return
        await asyncio.sleep(0.05)
    raise AssertionError(f"ai visuals did not settle within {timeout}s for {user_id}/{kind}")


def _select_report_visuals(report_id: uuid.UUID):
    return select(ReportFeatureVisual).where(ReportFeatureVisual.report_id == str(report_id))


async def _wait_for_report_visuals_terminal(db: AsyncSession, report_id: uuid.UUID, timeout: float = 3.0) -> None:
    deadline = asyncio.get_event_loop().time() + timeout
    terminal = {"generated", "failed"}
    while asyncio.get_event_loop().time() < deadline:
        result = await db.execute(_select_report_visuals(report_id).execution_options(populate_existing=True))
        rows = result.scalars().all()
        if len(rows) == len(ANALYSIS_FEATURES) and all(row.status in terminal for row in rows):
            return
        await asyncio.sleep(0.05)
    raise AssertionError(f"report visuals did not settle within {timeout}s for report {report_id}")


class TestResumeAnalysisPipeline:
    """Direct tests of the three resume branches, independent of the
    reconciler's own staleness-detection query. Assertions use a
    before/after delta on ai_recorder.call_count, not an absolute value --
    POST /analysis's own trigger_analysis already schedules
    run_analysis_pipeline as a background task, which can race a test's own
    direct pipeline call (see test_chat_flow.py's baseline_calls pattern
    for the same reasoning)."""

    async def test_cv_not_done_reruns_whole_pipeline(
        self, client: AsyncClient, email_sender, ai_recorder, db, monkeypatch
    ):
        # Suppresses trigger_analysis's own auto-schedule so CV genuinely
        # never runs before this test's own resume_analysis_pipeline call --
        # simulates a crash before the background pipeline got a chance to
        # start at all.
        monkeypatch.setattr("app.services.analysis_service.schedule_background_task", lambda coro: coro.close())

        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "resume-cv-pending@example.com")
        await _complete_questionnaire(client, headers)
        await _complete_photos(client, headers)
        await _mark_paid(db, user_id)
        trigger = await client.post("/analysis", headers=headers)
        analysis_id = uuid.UUID(trigger.json()["id"])
        baseline = ai_recorder.call_count

        await resume_analysis_pipeline(analysis_id)

        record = await _refetch_analysis(db, analysis_id)
        assert record.status == "completed"
        assert record.facial_assessments is not None
        assert record.narrative_result is not None
        assert ai_recorder.call_count - baseline == 1

    async def test_cv_done_narrative_not_done_resumes_narrative_only(
        self, client: AsyncClient, email_sender, ai_recorder, db
    ):
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "resume-narrative-only@example.com")
        analysis_id = uuid.UUID(await _complete_paid_analysis(client, headers, db, user_id))
        await _settle_stray_background_tasks()

        record = await db.get(FacialAnalysisResult, analysis_id)
        record.status = "processing"
        record.narrative_result = None
        await db.commit()
        baseline = ai_recorder.call_count

        await resume_analysis_pipeline(analysis_id)

        record = await _refetch_analysis(db, analysis_id)
        assert record.status == "completed"
        assert record.narrative_result is not None
        assert ai_recorder.call_count - baseline == 1  # exactly one more narrative call, no CV re-run

    async def test_both_done_just_finalizes_with_no_new_ai_call(
        self, client: AsyncClient, email_sender, ai_recorder, db
    ):
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "resume-finalize-only@example.com")
        analysis_id = uuid.UUID(await _complete_paid_analysis(client, headers, db, user_id))
        await _settle_stray_background_tasks()

        record = await db.get(FacialAnalysisResult, analysis_id)
        record.status = "processing"  # narrative_result stays populated
        await db.commit()
        baseline = ai_recorder.call_count

        await resume_analysis_pipeline(analysis_id)

        record = await _refetch_analysis(db, analysis_id)
        assert record.status == "completed"
        assert ai_recorder.call_count == baseline  # unchanged -- no new AI call at all

    async def test_already_resolved_row_is_a_no_op(self, client: AsyncClient, email_sender, ai_recorder, db):
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "resume-already-done@example.com")
        analysis_id = uuid.UUID(await _complete_paid_analysis(client, headers, db, user_id))
        await _settle_stray_background_tasks()
        baseline = ai_recorder.call_count

        await resume_analysis_pipeline(analysis_id)  # status is already "completed"

        assert ai_recorder.call_count == baseline


class TestReconcileAnalyses:
    async def test_stuck_row_is_claimed_and_resumed(self, client: AsyncClient, email_sender, ai_recorder, db):
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "reconcile-stuck-analysis@example.com")
        analysis_id = uuid.UUID(await _complete_paid_analysis(client, headers, db, user_id))
        await _settle_stray_background_tasks()

        record = await db.get(FacialAnalysisResult, analysis_id)
        record.status = "processing"
        record.narrative_result = None
        record.updated_at = datetime.now(UTC) - _STALE
        await db.commit()
        baseline = ai_recorder.call_count

        resumed = await reconciler_service.reconcile_analyses(db)
        assert resumed == 1

        await _wait_for_analysis_status(db, analysis_id, "completed")
        record = await _refetch_analysis(db, analysis_id)
        assert record.narrative_result is not None
        assert ai_recorder.call_count - baseline == 1

    async def test_fresh_row_is_left_untouched(self, client: AsyncClient, email_sender, ai_recorder, db):
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "reconcile-fresh-analysis@example.com")
        analysis_id = uuid.UUID(await _complete_paid_analysis(client, headers, db, user_id))
        await _settle_stray_background_tasks()

        record = await db.get(FacialAnalysisResult, analysis_id)
        record.status = "processing"
        record.narrative_result = None
        record.updated_at = datetime.now(UTC) - _FRESH
        await db.commit()
        baseline = ai_recorder.call_count

        resumed = await reconciler_service.reconcile_analyses(db)
        assert resumed == 0

        record = await _refetch_analysis(db, analysis_id)
        assert record.status == "processing"  # untouched
        assert ai_recorder.call_count == baseline  # no new call


class TestReconcileAiVisuals:
    async def test_stuck_generating_row_is_reset_and_resumed(
        self, client: AsyncClient, email_sender, ai_recorder, db, monkeypatch
    ):
        fake_client = FakeImageClient()
        monkeypatch.setattr("app.services.ai_visual_service.get_image_generation_client", lambda: fake_client)
        # Suppresses only get_or_create_visuals' own initial auto-schedule
        # (rebinding the name in ai_visual_service's namespace only --
        # reconciler_service's own separately-imported reference to
        # schedule_background_task is unaffected) so the rows created below
        # start and stay "pending" until this test manually simulates the
        # crash, instead of racing a real (fake-backed) generation attempt.
        monkeypatch.setattr("app.services.ai_visual_service.schedule_background_task", lambda coro: coro.close())

        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "reconcile-stuck-visual@example.com")
        await _complete_paid_analysis(client, headers, db, user_id)
        rows = await ai_visual_service.get_or_create_visuals(db, user_id, "hairstyle")

        stuck_row = await db.get(AiVisual, rows[0].id)
        stuck_row.status = "generating"
        stuck_row.updated_at = datetime.now(UTC) - _STALE
        await db.commit()

        resumed = await reconciler_service.reconcile_ai_visuals(db)
        assert resumed == 1

        await _wait_for_ai_visuals_terminal(db, user_id, "hairstyle")
        result = await db.execute(_select_ai_visuals(user_id, "hairstyle").execution_options(populate_existing=True))
        all_rows = result.scalars().all()
        assert all(row.status == "generated" for row in all_rows)
        assert len(fake_client.calls) == len(rows)

    async def test_fresh_generating_row_is_left_untouched(
        self, client: AsyncClient, email_sender, ai_recorder, db, monkeypatch
    ):
        fake_client = FakeImageClient()
        monkeypatch.setattr("app.services.ai_visual_service.get_image_generation_client", lambda: fake_client)
        monkeypatch.setattr("app.services.ai_visual_service.schedule_background_task", lambda coro: coro.close())

        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "reconcile-fresh-visual@example.com")
        await _complete_paid_analysis(client, headers, db, user_id)
        rows = await ai_visual_service.get_or_create_visuals(db, user_id, "outfit")

        row = await db.get(AiVisual, rows[0].id)
        row.status = "generating"
        row.updated_at = datetime.now(UTC) - _FRESH
        await db.commit()

        resumed = await reconciler_service.reconcile_ai_visuals(db)
        assert resumed == 0
        assert fake_client.calls == []

        result = await db.execute(_select_ai_visuals(user_id, "outfit").execution_options(populate_existing=True))
        assert any(row.status == "generating" for row in result.scalars().all())


class TestReconcileReportVisuals:
    async def test_already_generated_features_are_never_regenerated_on_resume(
        self, client: AsyncClient, email_sender, ai_recorder, db, monkeypatch
    ):
        """Direct regression test for the Phase 21 resumability fix:
        generate_all_feature_visuals used to iterate all 11 ANALYSIS_FEATURES
        unconditionally, with no guard against a feature that already
        succeeded -- harmless before anything could call it a second time,
        but the reconciler is now exactly that second caller, and a resume
        must never re-pay for an already-generated image."""
        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "reconcile-report-visual@example.com")
        await _complete_paid_analysis(client, headers, db, user_id)
        report_resp = await client.post("/reports", headers=headers)
        report_id = uuid.UUID(report_resp.json()["id"])
        # No fake client installed yet for the report's own auto-scheduled
        # first generation attempt -- let that settle for real (no key
        # configured -> "failed" for all 11) before installing the fake
        # client, so it only ever sees the reconciler-triggered resume
        # calls this test actually cares about.
        await _wait_for_report_visuals_terminal(db, report_id)

        fake_client = FakeImageClient()
        monkeypatch.setattr("app.services.report_visual_service.get_image_generation_client", lambda: fake_client)

        result = await db.execute(select(ReportFeatureVisual).where(ReportFeatureVisual.report_id == str(report_id)))
        all_rows = result.scalars().all()
        already_generated_feature = "hair"
        for row in all_rows:
            if row.feature == already_generated_feature:
                row.status = "generated"
                row.content = b"already-generated-sentinel"
            else:
                row.status = "pending"
                row.content = None
            row.error_reason = None
            row.error_message = None
            row.updated_at = datetime.now(UTC) - _STALE
        await db.commit()

        resumed = await reconciler_service.reconcile_report_visuals(db)
        assert resumed == 1

        await _wait_for_report_visuals_terminal(db, report_id)
        result = await db.execute(
            select(ReportFeatureVisual).where(ReportFeatureVisual.report_id == str(report_id)).execution_options(
                populate_existing=True
            )
        )
        by_feature = {row.feature: row for row in result.scalars().all()}
        assert by_feature[already_generated_feature].content == b"already-generated-sentinel"
        assert all(row.status == "generated" for row in by_feature.values())
        # Exactly the 10 non-already-generated features were actually sent
        # to the image-gen client -- never the already-generated one.
        assert len(fake_client.calls) == len(ANALYSIS_FEATURES) - 1

    async def test_fresh_report_is_left_untouched(
        self, client: AsyncClient, email_sender, ai_recorder, db, monkeypatch
    ):
        fake_client = FakeImageClient()
        monkeypatch.setattr("app.services.report_visual_service.get_image_generation_client", lambda: fake_client)

        headers, user_id = await _auth_headers_and_user_id(client, email_sender, "reconcile-fresh-report@example.com")
        await _complete_paid_analysis(client, headers, db, user_id)
        await client.post("/reports", headers=headers)
        # Freshly created -- rows are "pending" with a recent updated_at,
        # not yet stale, and generation is presumably still legitimately
        # in flight (or about to be). The reconciler must not touch it.
        resumed = await reconciler_service.reconcile_report_visuals(db)
        assert resumed == 0


class TestRunReconcilerSweep:
    async def test_sweep_across_all_three_tables_is_a_no_op_when_nothing_is_stuck(self, db):
        # No stuck rows anywhere in a clean test DB -- must not raise, must
        # not schedule anything.
        await reconciler_service.run_reconciler_sweep()
