import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class AiVisual(Base):
    """One AI-generated visual-preview variation (FR-020, Milestone 2 Phase
    11) -- hairstyle/outfit/aging, shared by all three ai-visuals-* modules
    (see D:\\zzz\\ai-visuals-hairstyle\\plans.md decision 3 for why this is a
    separate table from report-enrichment's ReportFeatureVisual rather than
    a literal merge: that table's composite PK is fixed to the 11
    ANALYSIS_FEATURES with no room for N variations, attributes, a name, or
    a recommended flag).

    `variation_index` is 0-4 for hairstyle/outfit (5 catalog-selected
    variations) and 0-2 for aging (its 3 *generated* cards only -- the
    aging stack's "current" reference card is the user's own real photo,
    never a row here). `attributes` is a small kind-specific JSONB grid
    (Maintenance/Layers/Parting/Vibe for hairstyle; Occasion/Formality/
    Palette/Vibe for outfit; age_years/age_label for aging) -- kept as
    JSONB rather than fixed columns since the shape genuinely differs per
    kind, same "favor JSONB while shape is still moving" convention as
    database-design.md §4.
    """

    __tablename__ = "ai_visuals"
    __table_args__ = (UniqueConstraint("user_id", "kind", "variation_index"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    variation_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # "pending" (row inserted, generation not yet started) -> "generating"
    # -> "generated" | "failed". Terminal this phase -- no automatic retry
    # on read, no user-facing regenerate action (BR-006 cost control, same
    # posture as ReportFeatureVisual).
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    content: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    content_type: Mapped[str] = mapped_column(String(64), nullable=False, default="image/png")

    # e.g. "Soft Layered Bob" (hairstyle/outfit); aging uses this for its
    # age-step label ("Near term"/"Mid range"/"Longer range").
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # "QOVES CHOICE" badge equivalent -- exactly one True per (user_id, kind)
    # for hairstyle/outfit; always False for aging (nothing to recommend
    # among fixed age steps).
    is_recommended: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    attributes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    explanation: Mapped[str | None] = mapped_column(String(600), nullable=True)

    # Text, not String(N): a real vendor error payload (e.g. Gemini's 429
    # quota-exceeded response) is an unpredictable-length JSON/prose blob,
    # often well over 500 chars -- a bounded column here previously caused
    # asyncpg.StringDataRightTruncationError on the *failure-handling*
    # commit itself, silently crashing the background task and leaving the
    # row stuck at "generating" forever (see D:\\zzz\\ai-visuals-hairstyle\\
    # plans.md's incident note). Same "unbounded, AI text is unpredictable
    # length" posture as Message.content.
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # "timeout" | "rate_limited" | "content_policy_refusal" | "unknown" --
    # see image_generation_service.ImageGenerationError.
    error_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
