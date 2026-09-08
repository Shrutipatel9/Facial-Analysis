import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class QuestionnaireResponse(Base):
    """A single submitted pass through the 23-question onboarding
    questionnaire (FR-003, FR-004, BR-003).

    `answers` is JSON (question-id -> answer), not one column per question,
    per docs/database-design.md §2.4 -- the question set can still change
    during development without a migration. Keys/values are validated
    against the QUESTIONS constant in app/services/questionnaire_service.py
    at write time (see submit_response), not enforced by the column type.

    No uniqueness constraint on user_id: this is deliberately one-to-many
    (docs/database-design.md's User--1--*--Questionnaire Response), since a
    later report always links to a specific questionnaire_response_id.
    Phase 2 only ever creates the first row per user (one-and-done, no
    resubmission UI yet) -- see docs/onboarding_questionnaire_spec.md.
    """

    __tablename__ = "questionnaire_responses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    answers: Mapped[dict] = mapped_column(JSONB, nullable=False)
    disclaimer_accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
