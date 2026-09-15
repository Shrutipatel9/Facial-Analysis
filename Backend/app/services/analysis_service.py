"""Facial analysis orchestration (FR-007, FR-008, BR-004) -- ties together
photo_service, questionnaire_service, facial_measurement_service, and
ai_narrative_service.

Pay-before-analysis (see D:\\zzz\\payment\\plans.md): trigger_analysis
requires a succeeded Payment to already exist for the user -- it is the
literal server-side enforcement point for "payment before analysis start,
analysis only starts after payment." The trigger itself is still a
user-facing "Start Analysis" action (POST /analysis, see
components/analysis/AnalysisScreen.tsx), just now only reachable once
payment has already succeeded -- the payment webhook (payment_service.
handle_webhook_event) only flips Payment.status, it does not call this
function. The same guarded function also serves as the retry path if a
run failed (a "failed" row may be retried without paying again, since
payment already succeeded).

Processing mechanism: an in-process asyncio background task, not a new
task-queue (Celery/Redis) -- no queue exists anywhere in this stack, and a
single background call doesn't justify adding one (see
D:\\zzz\\facial-analysis-engine\\plans.md). Background tasks open their
OWN DB session (never the request-scoped one) since they outlive the
request that started them.
"""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.background_tasks import schedule_background_task
from app.core.cv_executor import run_cv_task
from app.db.session import async_session_factory
from app.exceptions import (
    AnalysisAlreadyExistsError,
    AnalysisNotFoundError,
    PaymentRequiredError,
    PhotoIdentityMismatchError,
    PhotoSetNotReadyError,
    QuestionnaireNotSubmittedError,
)
from app.models.facial_analysis_result import FacialAnalysisResult
from app.models.questionnaire_response import QuestionnaireResponse
from app.services import payment_service, photo_service, questionnaire_service
from app.services.ai_narrative_service import generate_narrative
from app.services.facial_assessment_service import extract_measurements_and_assessments
from app.services.facial_measurement_service import ANALYSIS_FEATURES
from app.services.photo_storage import get_photo_storage
from app.services.photo_validation_service import REQUIRED_ANGLES

logger = logging.getLogger(__name__)


async def _get_latest(db: AsyncSession, user_id: uuid.UUID) -> FacialAnalysisResult | None:
    result = await db.execute(
        select(FacialAnalysisResult)
        .where(FacialAnalysisResult.user_id == user_id)
        .order_by(FacialAnalysisResult.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def trigger_analysis(db: AsyncSession, user_id: uuid.UUID) -> FacialAnalysisResult:
    # Questionnaire checked first -- it's the earlier step in the actual
    # user flow (questionnaire -> photos -> payment -> analysis), so this
    # is the more useful error when multiple prerequisites are unmet.
    questionnaire_response = await questionnaire_service.get_latest_response(db, user_id)
    if questionnaire_response is None:
        raise QuestionnaireNotSubmittedError()

    if not await photo_service.is_photo_set_ready(db, user_id):
        raise PhotoSetNotReadyError()

    identity_check = await photo_service.get_identity_check(db, user_id)
    if identity_check is not None and not identity_check["consistent"]:
        raise PhotoIdentityMismatchError()

    # The actual "payment before analysis" enforcement point -- see module
    # docstring. Checked after questionnaire/photos (matches the user-facing
    # order: finish your profile and photos, THEN pay, THEN analysis runs)
    # but before the existing-analysis check, since an unpaid retry attempt
    # should read as "pay first," not "already exists."
    if await payment_service.get_succeeded_payment(db, user_id) is None:
        raise PaymentRequiredError()

    existing = await _get_latest(db, user_id)
    # A FAILED analysis may be retried (a new row, not an update-in-place
    # -- keeps a simple history) -- PROCESSING/COMPLETED may not, same
    # one-and-done posture as the questionnaire/photos. Payment already
    # succeeded, so a retry here costs the user nothing extra.
    if existing is not None and existing.status != "failed":
        raise AnalysisAlreadyExistsError()

    placeholder_measurements = {feature: None for feature in ANALYSIS_FEATURES}
    record = FacialAnalysisResult(
        user_id=user_id,
        questionnaire_response_id=questionnaire_response.id,
        status="processing",
        measurements=placeholder_measurements,
    )
    db.add(record)
    # Commits (not just flushes) before scheduling the background task --
    # same "commit, then schedule" convention as every other
    # schedule_background_task call site (ai_visual_service.get_or_create_
    # visuals, report_service.get_or_create_report). The background task
    # opens its OWN DB session (module docstring), so a flush-only record
    # is invisible to it: asyncio.create_task() below doesn't run
    # synchronously, and there are real await points between here and this
    # request's get_db-dependency commit (response serialization,
    # security-headers/CORS/rate-limit middleware) where the event loop can
    # hand control to the newly scheduled task first -- it would then query
    # for a row that, from its own session's perspective, was never
    # committed, log "analysis <id> not found", and return without ever
    # flipping status off "processing". The row is stuck forever after
    # that: trigger_analysis's own existing-analysis guard above only
    # allows a retry once status is "failed", never "processing" -- so
    # without this commit, a user who hits this race has no in-app way to
    # recover at all.
    await db.commit()
    await db.refresh(record)

    analysis_id = record.id
    schedule_background_task(run_analysis_pipeline(analysis_id))

    return record


async def run_analysis_pipeline(analysis_id: uuid.UUID) -> None:
    """CV/MediaPipe measurements followed immediately by the DeepSeek
    narrative call, all in one background task -- only ever scheduled after
    payment has already succeeded (see trigger_analysis), so there is no
    more reason to split the paid AI call out from the free CV step the way
    the earlier deferred-cost design did.

    `status` only flips to "completed" once BOTH steps have been attempted
    -- not right after CV extraction. The frontend polls GET /analysis/status
    and treats "completed" as "safe to move on and generate the report"; if
    status flipped early (CV done, narrative call still in flight -- a real
    DeepSeek call can take a while), the report would get assembled from a
    still-empty `narrative_result` and show only images/templated
    placeholders until a later reload happened to pick up the real content
    via report_service's re-assembly-on-read. Keeping the row "processing"
    for the narrative call's whole duration is what makes "completed"
    trustworthy as "the full report is actually ready."

    Never lets a CV-extraction failure vanish silently -- marks the row
    "failed" with a real error_message. A narrative-generation failure is
    treated more leniently: the user already paid and has valid
    measurements, so the row still reaches "completed" with `narrative_result`
    left null rather than failing outright -- report_assembly_service's
    templated fallback still gives the report something reasonable to show,
    and a manual re-invoke of this function is the practical retry path
    (see D:\\zzz\\payment\\plans.md's open items).
    """
    async with async_session_factory() as session:
        record = await session.get(FacialAnalysisResult, analysis_id)
        if record is None:
            logger.error("run_analysis_pipeline: analysis %s not found", analysis_id)
            return

        try:
            photos = await _load_photo_bytes(session, record.user_id)
            # Milestone 2 (FR-018): the combinator runs MediaPipe detection
            # exactly once and derives both the per-feature measurements
            # and the 5 facial assessments from it -- calling
            # extract_measurements() and extract_facial_assessments()
            # separately would each independently re-run the landmarker.
            measurements, assessments = await run_cv_task(extract_measurements_and_assessments, photos)
            record.measurements = {feature: value.to_dict() for feature, value in measurements.items()}
            record.facial_assessments = {category: value.to_dict() for category, value in assessments.items()}
            await session.commit()
        except Exception:  # noqa: BLE001 -- broad on purpose, see docstring
            logger.exception("Analysis pipeline failed for %s", analysis_id)
            await session.rollback()
            record = await session.get(FacialAnalysisResult, analysis_id)
            if record is not None:
                record.status = "failed"
                record.error_message = "Analysis failed unexpectedly."
                await session.commit()
            return

        try:
            questionnaire_response = await session.get(QuestionnaireResponse, record.questionnaire_response_id)
            narrative = await generate_narrative(
                measurements=measurements,
                questionnaire_answers=questionnaire_response.answers if questionnaire_response else {},
                photos=photos,
            )
            record.narrative_result = narrative.to_dict()
        except Exception:  # noqa: BLE001 -- broad on purpose, see docstring
            logger.exception("Narrative generation failed for %s", analysis_id)
            await session.rollback()
            record = await session.get(FacialAnalysisResult, analysis_id)
            if record is None:
                return

        record.status = "completed"
        record.completed_at = datetime.now(UTC)
        await session.commit()


async def _load_photo_bytes(db: AsyncSession, user_id: uuid.UUID) -> dict[str, bytes]:
    storage = get_photo_storage()
    status_by_angle = await photo_service.get_status_by_angle(db, user_id)
    photos: dict[str, bytes] = {}
    for angle in REQUIRED_ANGLES:
        photo = status_by_angle[angle.id]
        if photo is not None:
            photos[angle.id] = await storage.load(photo.storage_reference)
    return photos


async def get_status(db: AsyncSession, user_id: uuid.UUID) -> dict[str, object]:
    record = await _get_latest(db, user_id)
    if record is None:
        return {"status": "none", "analysis_id": None}
    return {"status": record.status, "analysis_id": str(record.id)}


async def get_analysis(db: AsyncSession, user_id: uuid.UUID, analysis_id: uuid.UUID) -> FacialAnalysisResult:
    result = await db.execute(
        select(FacialAnalysisResult).where(
            FacialAnalysisResult.id == analysis_id, FacialAnalysisResult.user_id == user_id
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise AnalysisNotFoundError()
    return record
