import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class Payment(Base):
    """A Stripe Checkout attempt gating this user's one analysis run
    (FR-015, FR-016, BR-001 -- see the "pay before analysis" flow in
    D:\\zzz\\payment\\plans.md). Tied to `user_id` only, not a report: a
    Payment is always created and resolved *before* any FacialAnalysisResult
    or Report exists for the user, so there is nothing to link it to yet.

    No DB-level uniqueness on user_id -- a user may have multiple Payment
    rows over time (e.g. a "pending" session that expired, then a fresh
    "succeeded" one) -- "has this user paid" is answered by querying for a
    `status="succeeded"` row, not by row cardinality.
    """

    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # The Stripe Checkout Session id -- the "stripe_reference" from
    # database-design.md §2.8.
    stripe_session_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")

    # Copied from configuration at creation time -- never re-read live, so a
    # later price change (OQ-002 is still open) never affects an
    # already-in-progress payment.
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
