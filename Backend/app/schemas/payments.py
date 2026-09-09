import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

PaymentStatus = Literal["pending", "succeeded", "failed"]


class CheckoutResponse(BaseModel):
    checkout_url: str


class PaymentStatusOut(BaseModel):
    """Mirrors GET /questionnaire/status, GET /photos/status, GET
    /analysis/status's shape -- lets the frontend guard chain and the
    paywall page both read from one endpoint. "failed" is folded into
    "unpaid" the same way report_service used to (a failed attempt can
    simply be retried)."""

    status: Literal["unpaid", "pending", "succeeded"]
    # Never hardcoded client-side (FR-016, OQ-002 stays open/configurable).
    price_cents: int
    price_currency: str


class PaymentOut(BaseModel):
    id: uuid.UUID
    status: PaymentStatus
    amount_cents: int
    currency: str
    created_at: datetime

    model_config = {"from_attributes": True}
