"""Report generation orchestration (FR-009-FR-014, BR-002) -- ties
together analysis_service's output with report_assembly_service and
report_pdf_service.

Payment now gates the START of analysis itself (analysis_service.
trigger_analysis, see D:\\zzz\\payment\\plans.md), not report content -- a
Report can only ever be created from an already-`"completed"` analysis,
which by construction never exists without a preceding succeeded payment.
There is therefore no more teaser/full-content split to enforce here; `full`
is always populated.

`sections` is still re-assembled on read (not frozen at creation) as a
defensive measure for one narrow case: the DeepSeek narrative call can fail
even after payment succeeds (a known gap, see D:\\zzz\\payment\\plans.md's
open items), leaving `narrative_result` null on an otherwise-"completed"
row. A manual re-invoke of analysis_service.run_analysis_pipeline is the
practical fix for that; re-assembling on read means the report picks up the
retried narrative automatically without needing to delete/recreate the row.
assemble_sections() is a pure, free function, so this costs nothing.

PDF rendering is deferred (lazily generated on first GET /reports/{id}/pdf
and cached in ReportPdfBlob) -- the cache is invalidated whenever
re-assembly picks up newly-available narrative content.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.background_tasks import schedule_background_task
from app.exceptions import (
    AnalysisNotCompletedError,
    ReportImageNotFoundError,
    ReportNotFoundError,
    ReportVisualNotFoundError,
)
from app.models.facial_analysis_result import FacialAnalysisResult
from app.models.report import Report
from app.models.report_feature_image import ReportFeatureImage
from app.models.report_feature_visual import ReportFeatureVisual
from app.models.report_pdf_blob import ReportPdfBlob
from app.models.user import User
from app.services import photo_service
from app.services.facial_measurement_service import ANALYSIS_FEATURES, extract_feature_crops
from app.services.photo_storage import get_photo_storage
from app.services.report_assembly_service import assemble_sections
from app.services.report_pdf_service import render_pdf
from app.services.report_visual_service import generate_all_feature_visuals


async def _get_latest_analysis(db: AsyncSession, user_id: uuid.UUID) -> FacialAnalysisResult | None:
    result = await db.execute(
        select(FacialAnalysisResult)
        .where(FacialAnalysisResult.user_id == user_id)
        .order_by(FacialAnalysisResult.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _get_by_analysis_id(db: AsyncSession, analysis_id: uuid.UUID) -> Report | None:
    result = await db.execute(select(Report).where(Report.analysis_result_id == analysis_id))
    return result.scalar_one_or_none()


async def _load_front_photo(db: AsyncSession, user_id: uuid.UUID) -> dict[str, bytes]:
    """Only the front angle is needed for feature-crop imagery (see
    facial_measurement_service.extract_feature_crops) -- unlike
    analysis_service._load_photo_bytes, which loads all three for the AI
    narrative call."""
    status_by_angle = await photo_service.get_status_by_angle(db, user_id)
    front = status_by_angle.get("front")
    if front is None:
        return {}
    storage = get_photo_storage()
    return {"front": await storage.load(front.storage_reference)}


async def _sync_sections(db: AsyncSession, record: Report, analysis: FacialAnalysisResult) -> Report:
    """Re-assembles `sections` if narrative_result has become available
    since this Report row was last written -- see module docstring for why
    this can still happen post-payment. Costs nothing when there is
    nothing new to pick up."""
    had_narrative = bool(record.sections.get("closing_recommendations"))
    has_narrative_now = analysis.narrative_result is not None
    if not (has_narrative_now and not had_narrative):
        return record

    new_sections = assemble_sections(
        analysis.measurements, analysis.narrative_result or {}, analysis.facial_assessments or {}
    )
    for feature in ANALYSIS_FEATURES:
        existing_feature = record.sections.get("features", {}).get(feature, {})
        new_sections["features"][feature]["has_image"] = existing_feature.get("has_image", False)
    record.sections = new_sections
    # The cached PDF (if any) was rendered without the narrative -- stale
    # now that real content exists, so force a regenerate on next download.
    record.pdf_reference = None
    await db.commit()
    await db.refresh(record)
    return record


async def get_or_create_report(db: AsyncSession, user_id: uuid.UUID) -> Report:
    """Idempotent get-or-create -- deliberately does NOT raise a
    duplicate-error the way analysis_service.trigger_analysis does.
    Repeated calls are free/safe here (no AI cost, no side effect beyond a
    cheap re-read), unlike triggering a paid analysis run."""
    analysis = await _get_latest_analysis(db, user_id)
    if analysis is None or analysis.status != "completed":
        raise AnalysisNotCompletedError()

    existing = await _get_by_analysis_id(db, analysis.id)
    if existing is not None:
        return await _sync_sections(db, existing, analysis)

    sections = assemble_sections(
        analysis.measurements, analysis.narrative_result or {}, analysis.facial_assessments or {}
    )

    photos = await _load_front_photo(db, user_id)
    crops = extract_feature_crops(photos)
    for feature in ANALYSIS_FEATURES:
        sections["features"][feature]["has_image"] = crops.get(feature) is not None

    record = Report(
        user_id=user_id,
        questionnaire_response_id=analysis.questionnaire_response_id,
        analysis_result_id=analysis.id,
        sections=sections,
        publish_state="published",
    )
    db.add(record)
    await db.flush()  # assigns record.id, needed by the feature-image/visual rows below
    for feature, image_bytes in crops.items():
        if image_bytes is not None:
            db.add(ReportFeatureImage(report_id=str(record.id), feature=feature, content=image_bytes))

    # Milestone 2 (FR-022): all 11 "pending" rows are inserted here,
    # synchronously and atomically with the rest of report creation -- this
    # is the one-time trigger signal for generate_all_feature_visuals below.
    # BR-006 cost control: get_or_create_report is otherwise safe to call
    # repeatedly (idempotent, free) -- this creation branch only ever runs
    # once per report, so paid Gemini generation only ever gets scheduled
    # once, never re-triggered by a later repeat GET.
    for feature in ANALYSIS_FEATURES:
        db.add(ReportFeatureVisual(report_id=str(record.id), feature=feature, status="pending"))

    await db.commit()
    await db.refresh(record)
    schedule_background_task(generate_all_feature_visuals(record.id))
    return record


async def list_reports(db: AsyncSession, user_id: uuid.UUID) -> list[Report]:
    result = await db.execute(
        select(Report).where(Report.user_id == user_id).order_by(Report.created_at.desc())
    )
    return list(result.scalars().all())


async def get_report(db: AsyncSession, user_id: uuid.UUID, report_id: uuid.UUID) -> Report:
    result = await db.execute(select(Report).where(Report.id == report_id, Report.user_id == user_id))
    record = result.scalar_one_or_none()
    if record is None:
        raise ReportNotFoundError()
    analysis = await db.get(FacialAnalysisResult, record.analysis_result_id)
    if analysis is not None:
        record = await _sync_sections(db, record, analysis)
    return record


async def get_feature_image(db: AsyncSession, user_id: uuid.UUID, report_id: uuid.UUID, feature: str) -> bytes:
    await get_report(db, user_id, report_id)  # 404s if not found/not owned
    image = await db.get(ReportFeatureImage, {"report_id": str(report_id), "feature": feature})
    if image is None:
        raise ReportImageNotFoundError()
    return image.content


async def _load_all_feature_images(db: AsyncSession, report_id: uuid.UUID) -> dict[str, bytes]:
    result = await db.execute(select(ReportFeatureImage).where(ReportFeatureImage.report_id == str(report_id)))
    return {row.feature: row.content for row in result.scalars().all()}


async def get_visuals_status(db: AsyncSession, user_id: uuid.UUID, report_id: uuid.UUID) -> dict[str, str]:
    """Milestone 2 (FR-022): {feature: status} for all 11 features, always
    fully keyed -- "not_attempted" for a pre-Milestone-2 report with no
    ReportFeatureVisual rows at all, matching FeatureSectionOut.visual_status'
    convention. Lightweight polling endpoint, mirrors GET /analysis/status'
    existing precedent (cheaper than re-fetching the full ReportOut on
    every poll tick while generation is in flight)."""
    await get_report(db, user_id, report_id)  # 404s if not found/not owned
    result = await db.execute(select(ReportFeatureVisual).where(ReportFeatureVisual.report_id == str(report_id)))
    by_feature = {row.feature: row.status for row in result.scalars().all()}
    return {feature: by_feature.get(feature, "not_attempted") for feature in ANALYSIS_FEATURES}


async def get_feature_visual(db: AsyncSession, user_id: uuid.UUID, report_id: uuid.UUID, feature: str) -> bytes:
    """Milestone 2 (FR-022). Same anti-enumeration posture as
    get_feature_image -- 404s (ReportVisualNotFoundError) for an unknown
    feature, a not-yet-generated row, or no row at all (pre-Milestone-2
    report), never a different error shape per case."""
    await get_report(db, user_id, report_id)  # 404s if not found/not owned
    visual = await db.get(ReportFeatureVisual, {"report_id": str(report_id), "feature": feature})
    if visual is None or visual.status != "generated" or visual.content is None:
        raise ReportVisualNotFoundError()
    return visual.content


async def _load_all_feature_visuals(db: AsyncSession, report_id: uuid.UUID) -> dict[str, bytes]:
    """Only status="generated" rows -- used by report_pdf_service.py's
    before/after rendering, which must never block on a pending/failed
    visual (report_template.md §16.4)."""
    result = await db.execute(select(ReportFeatureVisual).where(ReportFeatureVisual.report_id == str(report_id)))
    return {row.feature: row.content for row in result.scalars().all() if row.status == "generated" and row.content}


async def get_or_generate_pdf(db: AsyncSession, user_id: uuid.UUID, report_id: uuid.UUID) -> tuple[bytes, Report]:
    report = await get_report(db, user_id, report_id)
    reference = f"{report.id}.pdf"

    # Looked up unconditionally, not gated on report.pdf_reference being
    # set -- `reference` is deterministic from report.id alone, so a blob
    # row can already exist under it even when pdf_reference is None (e.g.
    # _sync_sections just reset it to force a narrative-driven re-render).
    # Treating that as "no blob exists" would make the render step below
    # try to INSERT a second row under the same primary key.
    blob = await db.get(ReportPdfBlob, reference)
    # Milestone 2 (FR-022): a cached PDF rendered before any AI visual had
    # finished generating would otherwise show no before/after images
    # forever -- if a feature's visual completed *after* this blob was
    # cached, treat the cache as stale and fall through to re-render, same
    # "pick up new content automatically" spirit as _sync_sections'
    # narrative-driven pdf_reference reset above.
    if (
        blob is not None
        and report.pdf_reference is not None
        and not await _has_visual_newer_than(db, report.id, blob.created_at)
    ):
        return blob.content, report

    user = await db.get(User, user_id)
    assert user is not None  # get_current_user already resolved this user

    images = await _load_all_feature_images(db, report.id)
    visuals = await _load_all_feature_visuals(db, report.id)
    pdf_bytes = render_pdf(report, user, images, visuals)

    if blob is not None:
        # `reference` is a stable, report-derived id (not content-addressed)
        # -- a stale-cache re-render must update this row in place, never
        # INSERT a second row under the same primary key.
        blob.content = pdf_bytes
        blob.content_type = "application/pdf"
        blob.created_at = datetime.now(UTC)
    else:
        db.add(ReportPdfBlob(id=reference, content=pdf_bytes, content_type="application/pdf"))
    report.pdf_reference = reference
    await db.commit()
    return pdf_bytes, report


async def _has_visual_newer_than(db: AsyncSession, report_id: uuid.UUID, cutoff: datetime) -> bool:
    result = await db.execute(
        select(ReportFeatureVisual).where(
            ReportFeatureVisual.report_id == str(report_id),
            ReportFeatureVisual.status == "generated",
            ReportFeatureVisual.updated_at > cutoff,
        )
    )
    return result.first() is not None
