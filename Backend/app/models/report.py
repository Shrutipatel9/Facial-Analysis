import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class Report(Base):
    """The client-facing 11-section report (FR-009-FR-014), assembled from
    a completed FacialAnalysisResult's measurements/narrative_result --
    see app/services/report_assembly_service.py. Report assembly does not
    call the AI again; it is a pure data transform of Phase 4's output plus
    static branded copy for the intro/preamble/limitations sections.

    No DB-level uniqueness on (user_id) / analysis_result_id -- "one report
    per user, 1:1 with the analysis result" is enforced in
    app/services/report_service.py (get_or_create_report), same
    service-layer-not-DB-constraint convention as
    FacialAnalysisResult/AnalysisAlreadyExistsError.
    """

    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    questionnaire_response_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questionnaire_responses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    analysis_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facial_analysis_results.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Full shape: app/services/report_assembly_service.assemble_sections().
    # Always fully populated -- there is no "processing" state for a Report
    # row (unlike FacialAnalysisResult), since assembly is synchronous.
    sections: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Set the first time GET /reports/{id}/pdf renders the PDF -- null means
    # "not yet generated", the trigger for report_service.get_or_generate_pdf
    # to render and cache it in ReportPdfBlob.
    pdf_reference: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # Phase 1: always "published" at creation time (BR-002, auto-publish, no
    # admin review). Forward-compatible field for Phase 2's Draft/Pending
    # Review/Approved states, same rationale as User.role.
    publish_state: Mapped[str] = mapped_column(String(16), nullable=False, default="published")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
