import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class Conversation(Base):
    """A user's AI Beauty Assistant chat thread (FR-019, Milestone 2
    Phase 12). One per user -- no DB-level uniqueness on `user_id`, same
    "service-layer enforces, not a DB constraint" convention already
    established by Report (see report.py's own docstring). Lazily created
    on the user's first chat message via chat_service.get_or_create_conversation,
    same idempotent pattern as report_service.get_or_create_report.
    """

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
