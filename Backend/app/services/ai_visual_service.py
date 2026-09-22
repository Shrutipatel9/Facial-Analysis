"""AI visual-preview orchestration (FR-020, Milestone 2 Phase 11) --
hairstyle/outfit/aging/potential, shared across all four ai-visuals-* kinds
(see D:\\zzz\\ai-visuals-hairstyle\\plans.md). Mirrors report_visual_service.py's
split (orchestration+DB here, the actual vendor call in
image_generation_service.py) and its BR-006 cost-control posture: generation
triggers exactly once per (user, kind) -- the row-existence check in
get_or_create_visuals is the one-time trigger signal, identical convention
to report_service.get_or_create_report. A content-policy refusal is
terminal; a transient failure (rate-limited/timeout) is retried the next
time get_or_create_visuals is called for that kind -- see
_all_retryable_failures/_reset_for_retry. POST /ai-visuals/{kind} (the same
call the frontend already makes on page load) doubles as the "retry"
action; there is no separate retry endpoint.

Hairstyle/outfit variations come from a templated catalog
(ai_visual_catalog.py), not a new AI text-generation call -- only the
preview image itself is AI-generated. Aging needs no catalog: its 3
generated steps are fixed by the confirmed cadence
(client_requirements.md FR-020, v1.25) -- the 4th "current" card is the
user's own real photo, never a row in this table. Potential (2026-09-18,
user-directed) is a single whole-face "after" image, also with no
catalog -- its one row's prompt is composed from the user's own
already-generated Priority Features recommendations (see
_build_potential_rows), not a new AI text call either.
"""

import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.background_tasks import schedule_background_task
from app.core.config import get_settings
from app.db.session import async_session_factory
from app.exceptions import AiVisualNotFoundError, AnalysisNotCompletedError
from app.models.ai_visual import AiVisual
from app.models.facial_analysis_result import FacialAnalysisResult
from app.services import photo_service
from app.services.ai_visual_catalog import HAIRSTYLE_CATALOG, OUTFIT_CATALOG, VariationArchetype, select_variations
from app.services.facial_measurement_service import ANALYSIS_FEATURES
from app.services.image_generation_service import (
    IDENTITY_PRESERVATION_INSTRUCTION,
    ImageGenerationError,
    generate_with_retry,
    get_image_generation_client,
)
from app.services.photo_storage import get_photo_storage
from app.services.report_assembly_service import assemble_sections, recommendation_text

logger = logging.getLogger(__name__)

VALID_KINDS: frozenset[str] = frozenset({"hairstyle", "outfit", "aging", "potential"})
# Generic, honest fallback when no feature is flagged "Needs Attention" --
# still worth generating *something* for "Potential" rather than skipping
# it, but never inventing a specific finding that doesn't exist.
_POTENTIAL_FALLBACK_SUGGESTION = "an overall healthier, refined, and well-groomed appearance"
_POTENTIAL_PRIORITY_FEATURE_COUNT = 3
# Transient Gemini failures that are safe to re-trigger without inventing
# a new user-facing "regenerate" product action -- BR-006 still forbids
# auto-retry of content-policy refusals.
_RETRYABLE_FAILURE_REASONS: frozenset[str] = frozenset({"rate_limited", "timeout"})
_VARIATION_COUNT = 5
# Confirmed cadence (client_requirements.md FR-020, v1.25) -- current/28 is
# the user's own real photo (never a row here); these are the 3 *generated*
# steps only.
_AGING_STEPS: tuple[tuple[int, str], ...] = ((31, "Near term"), (33, "Mid range"), (38, "Longer range"))
AGING_DISCLAIMER = "* Educational purpose only, not a forecast."

_CATALOGS: dict[str, tuple[VariationArchetype, ...]] = {"hairstyle": HAIRSTYLE_CATALOG, "outfit": OUTFIT_CATALOG}


def _all_retryable_failures(rows: list[AiVisual]) -> bool:
    return bool(rows) and all(
        row.status == "failed" and row.error_reason in _RETRYABLE_FAILURE_REASONS for row in rows
    )


async def _reset_for_retry(db: AsyncSession, rows: list[AiVisual]) -> None:
    for row in rows:
        row.status = "pending"
        row.error_reason = None
        row.error_message = None
        row.content = None
        row.content_type = "image/png"
    await db.commit()


async def reset_stuck_generating(db: AsyncSession, user_id: uuid.UUID, kind: str) -> None:
    """Reconciler-only (app/services/reconciler_service.py, Milestone 3.1
    Phase 21) -- resets a kind's row(s) still "generating" back to
    "pending" so the next generate_all_visuals call actually re-attempts
    them. Only ever one row per kind is "generating" at a time
    (generate_all_visuals uses asyncio.Semaphore(1) for ai-visuals), so
    this resets exactly the crash-orphaned row, never touching
    already-"generated" siblings. Unlike _reset_for_retry above, this
    never clears `content` -- a "generating" row never had content set
    yet, so there's nothing to clear."""
    rows = await _load_visuals(db, user_id, kind)
    for row in rows:
        if row.status == "generating":
            row.status = "pending"
            row.error_reason = None
            row.error_message = None
    await db.commit()



async def _get_latest_completed_analysis(db: AsyncSession, user_id: uuid.UUID) -> FacialAnalysisResult | None:
    result = await db.execute(
        select(FacialAnalysisResult)
        .where(FacialAnalysisResult.user_id == user_id, FacialAnalysisResult.status == "completed")
        .order_by(FacialAnalysisResult.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _load_visuals(db: AsyncSession, user_id: uuid.UUID, kind: str) -> list[AiVisual]:
    result = await db.execute(
        select(AiVisual)
        .where(AiVisual.user_id == user_id, AiVisual.kind == kind)
        .order_by(AiVisual.variation_index)
    )
    return list(result.scalars().all())


def _build_aging_rows(user_id: uuid.UUID) -> list[AiVisual]:
    return [
        AiVisual(
            user_id=user_id,
            kind="aging",
            variation_index=index,
            name=label,
            # Nothing to recommend among fixed age steps -- explicit, not
            # relying on the column's DB-level default.
            is_recommended=False,
            attributes={"age_years": age_years, "age_label": label},
        )
        for index, (age_years, label) in enumerate(_AGING_STEPS)
    ]


def _build_potential_rows(user_id: uuid.UUID, analysis: FacialAnalysisResult) -> list[AiVisual]:
    """Exactly one row -- "Potential" is a single whole-face "after" image,
    not a catalog of alternatives (no `_VARIATION_COUNT`/select_variations
    the way hairstyle/outfit have). Its prompt content is composed here
    (at row-creation time, stored in `explanation` for _build_prompt to
    read later -- same slot hairstyle/outfit already use to carry
    prompt-building data) from the same Priority Features data
    PriorityFeaturesList.tsx and the PDF's Overview page already show:
    the lowest-scoring "Needs Attention" features' own first
    recommendation each, reusing report_assembly_service.assemble_sections
    (a pure function, already computes this) rather than re-deriving
    feature scores here. No new AI text-generation call."""
    sections = assemble_sections(
        analysis.measurements or {}, analysis.narrative_result or {}, analysis.facial_assessments or {}
    )
    feature_scores = sections.get("feature_scores", {})
    priority_features = sorted(
        (
            feature
            for feature in ANALYSIS_FEATURES
            if (feature_scores.get(feature) or {}).get("available")
            and feature_scores[feature].get("score") is not None
            and feature_scores[feature].get("label") == "Needs Attention"
        ),
        key=lambda feature: feature_scores[feature]["score"],
    )[:_POTENTIAL_PRIORITY_FEATURE_COUNT]

    ideas: list[str] = []
    for feature in priority_features:
        feature_ideas = (sections.get("features", {}).get(feature) or {}).get("projected_potential") or []
        if feature_ideas:
            # `sections` is a previously-persisted Report.sections JSONB blob
            # (assemble_sections runs once at report-creation time, never
            # re-run on read) -- a report created before FR-025 shipped still
            # has projected_potential as bare strings forever, so this must
            # tolerate both shapes, same as report_assembly_service.
            ideas.append(recommendation_text(feature_ideas[0]))

    suggestion = "; ".join(ideas) if ideas else _POTENTIAL_FALLBACK_SUGGESTION
    return [
        AiVisual(
            user_id=user_id,
            kind="potential",
            variation_index=0,
            name="Your Potential",
            # Nothing to recommend among alternatives -- there's only one
            # row, same posture as aging's fixed steps.
            is_recommended=False,
            attributes={"priority_features": priority_features},
            explanation=suggestion,
        )
    ]


def _build_variation_rows(
    user_id: uuid.UUID, kind: str, face_shape: str | None, dimorphism_label: str | None
) -> list[AiVisual]:
    archetypes = select_variations(
        _CATALOGS[kind], face_shape=face_shape, dimorphism_label=dimorphism_label, count=_VARIATION_COUNT
    )
    return [
        AiVisual(
            user_id=user_id,
            kind=kind,
            variation_index=index,
            name=archetype.name,
            is_recommended=(index == 0),
            attributes=archetype.attributes,
            explanation=archetype.explanation,
        )
        for index, archetype in enumerate(archetypes)
    ]


async def get_or_create_visuals(db: AsyncSession, user_id: uuid.UUID, kind: str) -> list[AiVisual]:
    """Idempotent lazy get-or-create + trigger-once (BR-006). Raises
    AnalysisNotCompletedError if no completed analysis exists yet --
    mirrors report_service.get_or_create_report's own precondition, since
    both need the same finished CV pass (facial_assessments) to ground
    their content.

    Exception to trigger-once: if every row is a retryable failure
    (rate_limited / timeout), reset and schedule again -- otherwise a
    Gemini 429 storm permanently bricks the feature with no recovery.
    Content-policy refusals stay terminal.
    """
    existing = await _load_visuals(db, user_id, kind)
    if existing:
        if _all_retryable_failures(existing):
            await _reset_for_retry(db, existing)
            schedule_background_task(generate_all_visuals(user_id, kind))
            return await _load_visuals(db, user_id, kind)
        # Orphaned all-pending set (e.g. process died mid-run, or ops reset
        # after rate_limit) -- re-schedule without inserting duplicate rows.
        if all(row.status == "pending" for row in existing):
            schedule_background_task(generate_all_visuals(user_id, kind))
        return existing

    analysis = await _get_latest_completed_analysis(db, user_id)
    if analysis is None:
        raise AnalysisNotCompletedError()

    if kind == "aging":
        rows = _build_aging_rows(user_id)
    elif kind == "potential":
        rows = _build_potential_rows(user_id, analysis)
    else:
        assessments = analysis.facial_assessments or {}
        face_shape = (assessments.get("face_shape") or {}).get("label")
        dimorphism_label = (assessments.get("dimorphism") or {}).get("label")
        rows = _build_variation_rows(user_id, kind, face_shape, dimorphism_label)

    db.add_all(rows)
    await db.commit()
    schedule_background_task(generate_all_visuals(user_id, kind))
    return rows


def _build_prompt(kind: str, row: AiVisual) -> str:
    if kind == "aging":
        age_years = (row.attributes or {}).get("age_years")
        return (
            f"Using this photo of a person's face, generate a photorealistic age-progression image "
            f"showing this same person at approximately age {age_years}, naturally aged with realistic "
            f"skin and hair changes for that age gap. Do not add clothing or background changes beyond "
            f"natural aging. {IDENTITY_PRESERVATION_INSTRUCTION}"
        )
    if kind == "outfit":
        subject = f"outfit and styling: {row.name} -- {row.explanation}"
        return (
            f"Using this photo of a person's face and shoulders, generate a photorealistic shoulder-up "
            f"image showing them wearing this {subject} {IDENTITY_PRESERVATION_INSTRUCTION}"
        )
    if kind == "potential":
        # Whole-face, not one specific feature -- row.explanation was
        # composed in _build_potential_rows from the user's own Priority
        # Features recommendations (or the generic fallback phrase).
        return (
            f"Using this photo of a person's whole face, generate a single photorealistic 'after' "
            f"image illustrating these specific cosmetic suggestions applied together, naturally and "
            f"subtly, as one cohesive improved appearance: {row.explanation} "
            f"{IDENTITY_PRESERVATION_INSTRUCTION}"
        )
    subject = f"hairstyle: {row.name} -- {row.explanation}"
    return (
        f"Using this photo of a person's face, generate a photorealistic image showing them with this "
        f"{subject} {IDENTITY_PRESERVATION_INSTRUCTION}"
    )


async def generate_all_visuals(user_id: uuid.UUID, kind: str) -> None:
    """Background task, own DB session (outlives the request that scheduled
    it, same convention as report_visual_service.generate_all_feature_visuals).
    Bounded concurrency via the existing IMAGE_GEN_MAX_CONCURRENCY setting --
    generic to "image generation", not report-specific, so no new config."""
    settings = get_settings()
    async with async_session_factory() as session:
        status_by_angle = await photo_service.get_status_by_angle(session, user_id)
        front_status = status_by_angle.get("front")
        front_bytes: bytes | None = None
        if front_status is not None:
            storage = get_photo_storage()
            front_bytes = await storage.load(front_status.storage_reference)
        rows = await _load_visuals(session, user_id, kind)

    # AI Visuals fire 3–5 images per kind; keep concurrency at 1 so a single
    # Gemini quota window doesn't rate-limit the whole set into terminal
    # failure. Report feature visuals still use IMAGE_GEN_MAX_CONCURRENCY.
    semaphore = asyncio.Semaphore(1)
    await asyncio.gather(
        *(
            _generate_one_visual(
                row.id,
                kind,
                source_image=front_bytes,
                prompt=_build_prompt(kind, row),
                semaphore=semaphore,
                max_retries=max(settings.image_gen_max_retries, 3),
            )
            for row in rows
            if row.status != "generated"
        )
    )


async def _generate_one_visual(
    visual_id: uuid.UUID,
    kind: str,
    *,
    source_image: bytes | None,
    prompt: str,
    semaphore: asyncio.Semaphore,
    max_retries: int,
) -> None:
    async with semaphore:
        async with async_session_factory() as session:
            row = await session.get(AiVisual, visual_id)
            if row is None:
                logger.error("generate_all_visuals: no row for %s/%s", kind, visual_id)
                return
            if row.status == "generated" and row.content is not None:
                return
            if row.status == "generating":
                # Another worker already claimed this row.
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
                logger.warning("Visual generation failed for %s/%s: %s", kind, visual_id, exc)
                row.status = "failed"
                row.error_reason = exc.reason
                row.error_message = str(exc)
                await session.commit()
                return
            except Exception:  # noqa: BLE001 -- broad on purpose: one variation's unexpected error must never crash the gather() for the others
                logger.exception("Unexpected error generating visual for %s/%s", kind, visual_id)
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


async def get_visuals(db: AsyncSession, user_id: uuid.UUID, kind: str) -> list[AiVisual]:
    """Read-only, never auto-triggers -- returns [] if get_or_create_visuals
    (POST) hasn't been called yet for this (user, kind)."""
    return await _load_visuals(db, user_id, kind)


async def get_visual_image(db: AsyncSession, user_id: uuid.UUID, kind: str, variation_id: uuid.UUID) -> bytes:
    """Anti-enumeration 404 -- unknown id, wrong user/kind, or not-yet-generated
    all collapse to the same AiVisualNotFoundError, same posture as
    report_service.get_feature_visual."""
    row = await db.get(AiVisual, variation_id)
    if row is None or row.user_id != user_id or row.kind != kind or row.status != "generated" or row.content is None:
        raise AiVisualNotFoundError()
    return row.content
