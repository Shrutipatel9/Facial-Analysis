import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class Photo(Base):
    """One required-angle photo upload (FR-005, FR-006, BR-004, BR-005).

    One row per (user_id, angle) -- a retry upserts the same row rather
    than accumulating one row per attempt (see photo_service.upload_photo),
    so `uploaded_at` uses onupdate=func.now() to reflect the latest attempt.

    `angle` is validated against REQUIRED_ANGLES in
    app/services/photo_validation_service.py at write time, not a Postgres
    enum -- same migration-flexibility rationale as the questionnaire's
    JSONB `answers` (ASM-004 may still change the angle set).

    `validation_result` always carries all six checks (not just failures),
    e.g. {"checks": [{"check": "resolution", "passed": true, "reason":
    null}, ...]} -- lets the frontend render a full pass/fail checklist.
    """

    __tablename__ = "photos"
    __table_args__ = (UniqueConstraint("user_id", "angle", name="uq_photos_user_id_angle"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    angle: Mapped[str] = mapped_column(String(32), nullable=False)
    capture_method: Mapped[str] = mapped_column(String(16), nullable=False)
    storage_reference: Mapped[str] = mapped_column(String(512), nullable=False)
    validation_status: Mapped[str] = mapped_column(String(16), nullable=False)
    validation_result: Mapped[dict] = mapped_column(JSONB, nullable=False)

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
