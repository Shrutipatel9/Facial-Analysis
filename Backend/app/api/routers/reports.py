"""Report endpoints -- thin: all logic lives in app/services/report_service.py.
See docs/api-specification.md §7.
"""

import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.report import Report
from app.models.user import User
from app.schemas.reports import ReportFullContentOut, ReportOut, ReportSummaryOut, ReportTeaserOut
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["reports"])


def _to_report_out(record: Report) -> ReportOut:
    """Projects the stored `sections` JSONB blob into the response DTO.
    `full` is always populated -- a Report can only ever be created from an
    already-`"completed"` analysis, which never exists without a preceding
    succeeded payment (analysis_service.trigger_analysis's own guard) --
    see report_service.py's module docstring."""
    sections = record.sections
    features = sections.get("features", {})
    teaser = ReportTeaserOut(
        intro=sections.get("intro", ""),
        feature_summaries={name: data.get("summary_callout", "") for name, data in features.items()},
    )
    full = ReportFullContentOut(
        understanding_your_results=sections.get("understanding_your_results", ""),
        limitations=sections.get("limitations", ""),
        features=features,
        recommendations=sections.get("recommendations", {}),
        closing_recommendations=sections.get("closing_recommendations", ""),
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
    return _to_report_out(record)


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
    return _to_report_out(record)


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
