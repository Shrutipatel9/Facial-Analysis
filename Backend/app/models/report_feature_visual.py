from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class ReportFeatureVisual(Base):
    """An AI-generated before/after image for one report feature (FR-022,
    Milestone 2), produced by image_generation_service.py /
    report_visual_service.py. Deliberately a separate table from
    ReportFeatureImage (the existing, synchronous/free crop-image table),
    not an extension of it -- generated visuals need a row to exist
    *before* content does (`status="pending"`), and need
    status/error/attempt-count fields a crop has no use for. Overloading
    ReportFeatureImage's `content: bytes NOT NULL` contract to mean
    "not yet generated" via NULL would make that column's existing meaning
    ambiguous for every caller that already reads it.

    One row per (report_id, feature) -- composite PK, same shape
    convention as ReportFeatureImage. All 11 ANALYSIS_FEATURES rows are
    inserted synchronously (all "pending") the first time a report is
    created (report_service.get_or_create_report) -- their mere existence
    is the "generation already triggered for this report" signal, since
    triggering the paid Gemini calls must happen at most once per report
    (BR-006 cost control), not on every repeat GET.
    """

    __tablename__ = "report_feature_visuals"

    report_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("reports.id", ondelete="CASCADE"), primary_key=True
    )
    feature: Mapped[str] = mapped_column(String(32), primary_key=True)

    # "pending" (row inserted, generation not yet started) -> "generating"
    # -> "generated" | "failed". Terminal this phase -- no automatic retry
    # on read, no user-facing regenerate action (both would reopen the
    # uncontrolled-repeat-spend problem the once-per-report trigger exists
    # to prevent).
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    content: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    content_type: Mapped[str] = mapped_column(String(64), nullable=False, default="image/png")

    # Text, not String(N): a real vendor error payload (e.g. Gemini's 429
    # quota-exceeded response) is an unpredictable-length JSON/prose blob,
    # often well over 500 chars -- a bounded column here previously caused
    # asyncpg.StringDataRightTruncationError on the *failure-handling*
    # commit itself, silently crashing the background task and leaving the
    # row stuck at "generating" forever. Same fix as AiVisual.error_message.
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # "timeout" | "rate_limited" | "content_policy_refusal" | "unknown" --
    # see image_generation_service.ImageGenerationError. Only
    # timeout/rate_limited are retried (up to Settings.image_gen_max_retries)
    # before landing here as "failed"; content_policy_refusal never retries.
    error_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
