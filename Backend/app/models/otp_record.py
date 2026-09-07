import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class OTPRecord(Base):
    """A single OTP challenge.

    The row's own `id` doubles as the opaque `challenge_id` the frontend
    holds between step 1 (email+password) and step 2 (OTP submission) --
    there is no separate challenge-id column.

    Only one OTPRecord is "active" (not consumed, not expired) per user at a
    time in practice: requesting a new one (register/login retry, resend)
    supersedes the previous one by creating a new row rather than mutating
    the old one, so a stale challenge_id reliably 404s instead of silently
    validating against a code that's no longer the "current" one (AUTH-011).
    """

    __tablename__ = "otp_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    purpose: Mapped[str] = mapped_column(String(16), nullable=False)  # "signup" | "login"

    # HMAC-SHA256(code, OTP_PEPPER) -- never the plaintext code (AUTH-011).
    otp_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    consumed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
