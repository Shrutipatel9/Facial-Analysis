import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class FacialAnalysisResult(Base):
    """The raw output of the CV measurement + AI narrative pipeline
    (FR-007, FR-008) -- one row per analysis run.

    `report-generation` (Phase 5) reads `measurements`/`narrative_result`
    and wraps them with intro/preamble/limitations/before-after framing
    into the client-facing Report; it does not re-run the AI call.

    No DB-level uniqueness on user_id -- "one analysis per user, no
    re-run" is enforced in app/services/analysis_service.py
    (AnalysisAlreadyExistsError), not a DB constraint, since a future
    re-analysis feature would only need a service-layer change.
    """

    __tablename__ = "facial_analysis_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    questionnaire_response_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questionnaire_responses.id", ondelete="CASCADE"), nullable=False, index=True
    )

    status: Mapped[str] = mapped_column(String(16), nullable=False, default="processing")

    # Always keyed by all 11 ANALYSIS_FEATURES (facial_measurement_service.py)
    # -- Hair/Neck carry null geometry (AI-only coverage), not omitted keys.
    measurements: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Raw AI output: one entry per feature (narrative + summary-callout
    # draft + recommendation ideas) + a closing-recommendations draft.
    # Null until status="completed".
    narrative_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Milestone 2 (FR-018): the 5 ASSESSMENT_CATEGORIES from
    # facial_assessment_service.py (dimorphism/prototypicality/proportions/
    # symmetry/face_shape). Nullable -- unlike `measurements`, a row created
    # before this column existed has no backfill and should read as "not
    # yet computed", not a fabricated empty-but-required blob.
    facial_assessments: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Production hardening (Milestone 3.1, Phase 21) -- staleness signal for
    # app/services/reconciler_service.py's crash-recovery sweep: a row still
    # "processing" whose updated_at hasn't moved in a while means the
    # background pipeline that was working on it died (process restart)
    # rather than genuinely still being in flight. Same onupdate convention
    # already used by AiVisual/ReportFeatureVisual.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
