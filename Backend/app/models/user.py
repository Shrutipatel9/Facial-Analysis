import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class User(Base):
    """A registered (or pending-registration) user.

    `verification_status` starts "pending" at signup Step 1 and only becomes
    "verified" once OTP verification succeeds (WF-002) -- a pending row is
    reused across a signup retry rather than creating a duplicate (see
    docs/database-design.md §2.2).

    `otp_locked_until` lives here rather than on OTPRecord because a lockout
    must survive OTP regeneration (AUTH-011): a new OTPRecord is created on
    every resend, but the lockout window must persist across that.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Nullable at the column level only for pre-existing rows created before
    # this field existed -- required by RegisterRequest for every new
    # signup (FR-017 "welcome back" greeting uses this instead of an
    # email-derived guess; see ASM-009's revision in client_requirements.md).
    full_name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # AUTH-009: reserved for a future "admin" role (Phase 2); only "user" is
    # ever set in Phase 1.
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="user", server_default="user")

    verification_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", server_default="pending"
    )

    otp_locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
