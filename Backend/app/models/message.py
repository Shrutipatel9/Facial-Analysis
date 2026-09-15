import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class Message(Base):
    """One turn in a Conversation (FR-019, Milestone 2 Phase 12) -- `role`
    is "user" or "assistant". `content` is unbounded Text, not a bounded
    String, since an assistant reply's length isn't predictable the way
    this project's other short text columns are. The user's own message is
    persisted immediately when sent (before any AI call), so it's never
    lost even if streaming the reply subsequently fails -- see
    chat_service.stream_reply.
    """

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
