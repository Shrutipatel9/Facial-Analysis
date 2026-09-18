"""Report endpoints -- thin: all logic lives in app/services/report_service.py.
See docs/api-specification.md §7.
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.facial_analysis_result import FacialAnalysisResult
from app.models.report import Report
from app.models.user import User
from app.schemas.reports import ReportFullContentOut, ReportOut, ReportSummaryOut, ReportTeaserOut
from app.services import report_service
from app.services.report_assembly_service import normalize_recommendation_item

router = APIRouter(prefix="/reports", tags=["reports"])


def _normalized_recommendation_items(raw: Any) -> list[dict[str, Any]]:
    """FR-025 -- `record.sections` is a JSONB blob frozen once at report-
    creation time (assemble_sections is never re-run on read), so a Report
    created before FR-025 shipped still has its `recommendations`/
    `projected_potential` lists as bare strings forever, while a newly
    created one already has the structured-object shape. Normalizes both
    at the API boundary so ReportFullContentOut's RecommendationItemOut
    validation never fails on an old row."""
    if not isinstance(raw, list):
        return []
    return [normalized for idea in raw if (normalized := normalize_recommendation_item(idea)) is not None]


async def _to_report_out(db: AsyncSession, user_id: uuid.UUID, record: Report) -> ReportOut:
    """Projects the stored `sections` JSONB blob into the response DTO.
    `full` is always populated -- a Report can only ever be created from an
    already-`"completed"` analysis, which never exists without a preceding
    succeeded payment (analysis_service.trigger_analysis's own guard) --
    see report_service.py's module docstring."""
    sections = record.sections
    features = sections.get("features", {})

    # Milestone 2 (FR-022): fold each feature's visual_status into its
    # section entry -- a separate DB read (report_service.get_visuals_status)
    # rather than something assemble_sections could have baked into
    # `sections` itself, since generation status changes independently of
    # (and faster than) the report's own content re-sync.
    visual_statuses = await report_service.get_visuals_status(db, user_id, record.id)
    features_with_visual_status: dict[str, Any] = {
        feature: {
            **data,
            "visual_status": visual_statuses.get(feature, "not_attempted"),
            "projected_potential": _normalized_recommendation_items(data.get("projected_potential")),
        }
        for feature, data in features.items()
    }
    recommendations = {
        tier: _normalized_recommendation_items(items) for tier, items in sections.get("recommendations", {}).items()
    }

    # Dashboard consolidation -- real elapsed CV+AI pipeline time, for the
    # Dashboard's "Analysis Time" stat. Never fabricated: null whenever
    # completed_at is null (narrative-generation still pending or failed
    # after CV succeeded, see analysis_service.run_analysis_pipeline's own
    # docstring), not "time since photo upload" (would conflate user idle
    # time with actual processing time).
    analysis = await db.get(FacialAnalysisResult, record.analysis_result_id)
    analysis_duration_seconds = (
        (analysis.completed_at - analysis.created_at).total_seconds()
        if analysis is not None and analysis.completed_at is not None
        else None
    )

    teaser = ReportTeaserOut(
        intro=sections.get("intro", ""),
        feature_summaries={name: data.get("summary_callout", "") for name, data in features.items()},
    )
    full = ReportFullContentOut(
        understanding_your_results=sections.get("understanding_your_results", ""),
        limitations=sections.get("limitations", ""),
        features=features_with_visual_status,
        recommendations=recommendations,
        closing_recommendations=sections.get("closing_recommendations", ""),
        facial_assessments=sections.get("facial_assessments", {}),
        feature_scores=sections.get("feature_scores", {}),
        overall_score=sections.get("overall_score"),
        harmony_chart=sections.get("harmony_chart", {}),
        analysis_duration_seconds=analysis_duration_seconds,
        facial_age=sections.get("facial_age"),
        hair_loss=sections.get("hair_loss"),
    )

    return ReportOut(
        id=record.id,
        publish_state=record.publish_state,
        created_at=record.created_at,
        teaser=teaser,
        full=full,
    )


@router.post("", response_model=ReportOut)
async def create_report(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ReportOut:
    record = await report_service.get_or_create_report(db, user.id)
    return await _to_report_out(db, user.id, record)


@router.get("", response_model=list[ReportSummaryOut])
async def list_reports(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[ReportSummaryOut]:
    records = await report_service.list_reports(db, user.id)
    return [ReportSummaryOut.model_validate(record) for record in records]


@router.get("/{report_id}", response_model=ReportOut)
async def get_report(
    report_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportOut:
    record = await report_service.get_report(db, user.id, report_id)
    return await _to_report_out(db, user.id, record)


@router.get("/{report_id}/pdf")
async def get_report_pdf(
    report_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    pdf_bytes, report = await report_service.get_or_generate_pdf(db, user.id, report_id)
    filename = f"facial_report_{report.created_at:%Y-%m-%d}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{report_id}/features/{feature}/image")
async def get_report_feature_image(
    report_id: uuid.UUID,
    feature: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    image_bytes = await report_service.get_feature_image(db, user.id, report_id, feature)
    return Response(content=image_bytes, media_type="image/jpeg")


@router.get("/{report_id}/features/{feature}/visual")
async def get_report_feature_visual(
    report_id: uuid.UUID,
    feature: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Milestone 2 (FR-022) -- 200 image bytes only once generation has
    actually completed for this feature; 404 otherwise (pending/generating/
    failed/not_attempted all collapse to the same ReportVisualNotFoundError,
    same anti-enumeration posture as get_report_feature_image). Frontend
    should check `visual_status` on the report response before calling this,
    same convention as `has_image` for the crop endpoint."""
    visual_bytes = await report_service.get_feature_visual(db, user.id, report_id, feature)
    return Response(content=visual_bytes, media_type="image/png")


@router.get("/{report_id}/visuals/status")
async def get_report_visuals_status(
    report_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Milestone 2 (FR-022) -- lightweight {feature: status} polling
    endpoint for the ~11 features' AI visual generation, mirroring
    GET /analysis/status's existing precedent. Cheaper than re-fetching the
    full ReportOut on every poll tick while generation is in flight."""
    return await report_service.get_visuals_status(db, user.id, report_id)
