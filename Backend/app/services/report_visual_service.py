"""Per-feature AI before/after visual generation orchestration (FR-022,
Milestone 2) -- the background-task counterpart to
image_generation_service.py's client, same split as analysis_service.py
(orchestration + DB) vs. ai_narrative_service.py (the AI call itself).

Triggered exactly once per report: report_service.get_or_create_report's
creation branch inserts all 11 ReportFeatureVisual rows synchronously
(cheap, no cost) as "pending", then schedules generate_all_feature_visuals
as a background task -- the row-existence check there (not here) is what
prevents a repeat GET /reports/{id} from re-triggering paid generation
(BR-006). Each feature transitions pending -> generating -> (generated|
failed) independently; one feature's failure never affects another's row
or blocks the rest (report_template.md §16.4's existing rule, carried
forward from the pre-Milestone-2 report design)."""

import asyncio
import logging
import uuid

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import async_session_factory
from app.models.facial_analysis_result import FacialAnalysisResult
from app.models.report import Report
from app.models.report_feature_image import ReportFeatureImage
from app.models.report_feature_visual import ReportFeatureVisual
from app.services import photo_service
from app.services.facial_measurement_service import ANALYSIS_FEATURES, extract_feature_crops
from app.services.image_generation_service import (
    IDENTITY_PRESERVATION_INSTRUCTION,
    ImageGenerationError,
    generate_with_retry,
    get_image_generation_client,
)
from app.services.photo_storage import get_photo_storage
from app.services.report_assembly_service import recommendation_text

logger = logging.getLogger(__name__)

_DEFAULT_PROMPT_SUGGESTION = "a subtle, natural cosmetic refinement to this area"


def _select_source_image(
    feature: str, persisted_crops: dict[str, bytes], crops: dict[str, bytes | None]
) -> bytes | None:
    """A feature-specific crop only -- persisted (already-generated and
    stored `ReportFeatureImage` bytes) takes priority over a freshly
    extracted one, and neither ever falls back to the full, uncropped
    front photo (2026-09-17, user-reported: an "eyes" visual came back
    showing the nose instead, because that fallback sent the whole face
    as the source image while the prompt still named one specific
    feature). Returns None when no crop exists for this feature at all --
    `_generate_one_feature_visual` turns that into a clean "failed" row,
    which is the correct outcome, not a mismatched image."""
    return persisted_crops.get(feature) or crops.get(feature)


def _build_prompt(feature: str, narrative_result: dict) -> str:
    feature_label = feature.replace("_", " ").title()
    feature_entry = (narrative_result or {}).get("features", {}).get(feature, {})
    ideas = feature_entry.get("recommendation_ideas") or []
    suggestion = recommendation_text(ideas[0]) if ideas else _DEFAULT_PROMPT_SUGGESTION
    suggestion = suggestion or _DEFAULT_PROMPT_SUGGESTION
    return (
        f"Using this photo of a person's {feature_label.lower()}, generate a photorealistic "
        f"'after' image illustrating this specific cosmetic suggestion: {suggestion} "
        f"{IDENTITY_PRESERVATION_INSTRUCTION}"
    )


async def generate_all_feature_visuals(report_id: uuid.UUID) -> None:
    """Background task -- own DB session (outlives the request that
    scheduled it, same convention as analysis_service.run_analysis_pipeline).
    Bounded concurrency via IMAGE_GEN_MAX_CONCURRENCY caps burst spend/
    rate-limit exposure across the 11 features."""
    settings = get_settings()
    async with async_session_factory() as session:
        report = await session.get(Report, report_id)
        if report is None:
            logger.error("generate_all_feature_visuals: report %s not found", report_id)
            return
        analysis = await session.get(FacialAnalysisResult, report.analysis_result_id)
        narrative_result = (analysis.narrative_result if analysis else None) or {}
        user_id = report.user_id

        status_by_angle = await photo_service.get_status_by_angle(session, user_id)
        front_status = status_by_angle.get("front")
        front_bytes: bytes | None = None
        if front_status is not None:
            storage = get_photo_storage()
            front_bytes = await storage.load(front_status.storage_reference)
        crops = extract_feature_crops({"front": front_bytes}) if front_bytes is not None else {}

        image_rows = await session.execute(
            select(ReportFeatureImage).where(ReportFeatureImage.report_id == str(report_id))
        )
        persisted_crops = {row.feature: row.content for row in image_rows.scalars().all()}

    semaphore = asyncio.Semaphore(settings.image_gen_max_concurrency)
    await asyncio.gather(
        *(
            _generate_one_feature_visual(
                report_id,
                feature,
                source_image=_select_source_image(feature, persisted_crops, crops),
                prompt=_build_prompt(feature, narrative_result),
                semaphore=semaphore,
                max_retries=settings.image_gen_max_retries,
            )
            for feature in ANALYSIS_FEATURES
        )
    )


async def _generate_one_feature_visual(
    report_id: uuid.UUID,
    feature: str,
    *,
    source_image: bytes | None,
    prompt: str,
    semaphore: asyncio.Semaphore,
    max_retries: int,
) -> None:
    async with semaphore:
        async with async_session_factory() as session:
            row = await session.get(ReportFeatureVisual, {"report_id": str(report_id), "feature": feature})
            if row is None:
                logger.error("generate_all_feature_visuals: no pending row for %s/%s", report_id, feature)
                return

            if source_image is None:
                row.status = "failed"
                row.error_reason = "unknown"
                row.error_message = "No source photo available to generate a visual from."
                await session.commit()
                return

            row.status = "generating"
            row.attempt_count += 1
            await session.commit()

            try:
                client = get_image_generation_client()
                image_bytes = await generate_with_retry(
                    client, source_image=source_image, prompt=prompt, max_retries=max_retries
                )
            except ImageGenerationError as exc:
                logger.warning("Visual generation failed for %s/%s: %s", report_id, feature, exc)
                row.status = "failed"
                row.error_reason = exc.reason
                row.error_message = str(exc)
                await session.commit()
                return
            except Exception:  # noqa: BLE001 -- broad on purpose: one feature's unexpected error must never crash the gather() for the other 10
                logger.exception("Unexpected error generating visual for %s/%s", report_id, feature)
                row.status = "failed"
                row.error_reason = "unknown"
                row.error_message = "Visual generation failed unexpectedly."
                await session.commit()
                return

            row.status = "generated"
            row.content = image_bytes
            row.content_type = "image/png"
            row.error_message = None
            row.error_reason = None
            await session.commit()
