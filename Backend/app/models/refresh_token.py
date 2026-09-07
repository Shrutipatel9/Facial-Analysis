import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class RefreshToken(Base):
    """A refresh-token session record.

    The raw refresh token is a `secrets.token_urlsafe(64)` opaque string and
    is NEVER stored -- only its SHA-256 hash (`token_hash`), so a database
    read alone can't be used to forge a session (AUTH-010).

    `family_id` is constant across an entire rotation chain (every refresh
    call rotates to a new row that shares the same family_id, via
    `replaced_by_id`). This is what makes reuse detection possible: if a
    token whose row already has `revoked_at` set is presented again, every
    non-revoked row sharing that family_id gets revoked too (AUTH-012) --
    the family_id is the unit of "this is one continuous session lineage",
    and reuse of a superseded token is treated as evidence the whole lineage
    may be compromised.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("refresh_tokens.id", ondelete="SET NULL"), nullable=True
    )
