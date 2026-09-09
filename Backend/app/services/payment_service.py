"""Stripe payment orchestration (FR-015, FR-016, BR-001) -- gates the START
of analysis itself, not just the report's full content: a user must have a
succeeded Payment before analysis_service.trigger_analysis will create a
FacialAnalysisResult row at all. See D:\\zzz\\payment\\plans.md.

Uses Stripe's hosted Checkout (mode="payment", a redirect to a
Stripe-hosted page) rather than handling card data ourselves at all --
docs/security.md §7's explicit recommendation. The webhook, not the
client-side success redirect, is the source of truth for "payment
succeeded" (the redirect can be spoofed, interrupted, or replayed; the
signed webhook cannot).

The webhook only ever flips Payment.status -- it deliberately does NOT
trigger analysis itself. "Payment before analysis start" is enforced by
trigger_analysis's own guard (PaymentRequiredError for an unpaid attempt);
the actual trigger stays a user-facing "Start Analysis" action on
/analysis (POST /analysis), same as before this module existed, just now
only reachable once payment has already succeeded. This is a deliberate
UX choice: the pipeline can finish in a couple of seconds for a fast
provider response, and auto-triggering it from the webhook made the
"analyzing" step invisible -- the user would land back in the app with a
report already sitting there, with no sense that anything had run.
"""

import logging
import uuid
from functools import lru_cache
from typing import Any

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.exceptions import (
    AlreadyPaidError,
    InvalidWebhookSignatureError,
    PhotoSetNotReadyError,
    QuestionnaireNotSubmittedError,
)
from app.models.payment import Payment
from app.models.user import User
from app.services import photo_service, questionnaire_service

logger = logging.getLogger(__name__)


@lru_cache
def get_stripe_client() -> Any:
    settings = get_settings()
    if not settings.stripe_secret_key:
        raise RuntimeError(
            "STRIPE_SECRET_KEY is not configured -- add a real key to Backend/.env before "
            "creating a checkout session."
        )
    stripe.api_key = settings.stripe_secret_key
    return stripe


async def get_succeeded_payment(db: AsyncSession, user_id: uuid.UUID) -> Payment | None:
    result = await db.execute(
        select(Payment)
        .where(Payment.user_id == user_id, Payment.status == "succeeded")
        .order_by(Payment.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_latest_payment(db: AsyncSession, user_id: uuid.UUID) -> Payment | None:
    """Regardless of status -- used to surface "pending"/"failed" in the
    API response, not just the binary paid/unpaid check."""
    result = await db.execute(
        select(Payment).where(Payment.user_id == user_id).order_by(Payment.created_at.desc()).limit(1)
    )
    return result.scalar_one_or_none()


async def get_status(db: AsyncSession, user_id: uuid.UUID) -> dict[str, object]:
    settings = get_settings()
    payment = await get_latest_payment(db, user_id)
    # A "failed" attempt can simply be retried -- the API never
    # distinguishes "failed" from "unpaid" (the Payment row itself still
    # records it, same posture the report-DTO mapping used pre-refactor).
    raw_status = payment.status if payment is not None else "unpaid"
    status = "unpaid" if raw_status == "failed" else raw_status
    return {
        "status": status,
        "price_cents": settings.report_price_cents,
        "price_currency": settings.report_price_currency,
    }


async def create_checkout_session(db: AsyncSession, user: User) -> str:
    # Same prerequisite order as analysis_service.trigger_analysis's own
    # guards (questionnaire -> photos) -- paying before either is ready
    # would leave the post-payment auto-trigger unable to start anything.
    questionnaire_response = await questionnaire_service.get_latest_response(db, user.id)
    if questionnaire_response is None:
        raise QuestionnaireNotSubmittedError()

    if not await photo_service.is_photo_set_ready(db, user.id):
        raise PhotoSetNotReadyError()

    existing = await get_succeeded_payment(db, user.id)
    if existing is not None:
        raise AlreadyPaidError()

    settings = get_settings()
    client = get_stripe_client()
    session = client.checkout.Session.create(
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": settings.report_price_currency,
                    "unit_amount": settings.report_price_cents,
                    "product_data": {"name": "FaceIQ Facial Analysis Report"},
                },
                "quantity": 1,
            }
        ],
        customer_email=user.email,
        success_url=f"{settings.frontend_base_url}/payment?payment=success",
        cancel_url=f"{settings.frontend_base_url}/payment?payment=cancelled",
        metadata={"user_id": str(user.id)},
    )

    db.add(
        Payment(
            user_id=user.id,
            stripe_session_id=session.id,
            status="pending",
            amount_cents=settings.report_price_cents,
            currency=settings.report_price_currency,
        )
    )
    await db.commit()
    return str(session.url)


async def _get_payment_by_session_id(db: AsyncSession, session_id: str) -> Payment | None:
    result = await db.execute(select(Payment).where(Payment.stripe_session_id == session_id))
    return result.scalar_one_or_none()


async def handle_webhook_event(db: AsyncSession, payload: bytes, sig_header: str) -> None:
    settings = get_settings()
    client = get_stripe_client()
    try:
        event = client.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
    except (ValueError, stripe.SignatureVerificationError) as exc:
        raise InvalidWebhookSignatureError() from exc

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        await _mark_succeeded(db, data["id"])
    elif event_type in ("checkout.session.expired", "payment_intent.payment_failed"):
        payment = await _get_payment_by_session_id(db, data.get("id", ""))
        if payment is not None:
            payment.status = "failed"
            await db.commit()
    # Any other event type is intentionally ignored -- Stripe sends many
    # event categories we don't act on; only the two above matter here.


async def _mark_succeeded(db: AsyncSession, session_id: str) -> None:
    payment = await _get_payment_by_session_id(db, session_id)
    if payment is None:
        logger.error("Webhook checkout.session.completed for unknown session %s", session_id)
        return
    if payment.status == "succeeded":
        return  # already processed -- Stripe may redeliver the same event
    payment.status = "succeeded"
    await db.commit()
    # Deliberately does NOT trigger analysis -- see module docstring. The
    # user starts it themselves on /analysis once they're back in the app.


async def list_payments(db: AsyncSession, user_id: uuid.UUID) -> list[Payment]:
    result = await db.execute(select(Payment).where(Payment.user_id == user_id).order_by(Payment.created_at.desc()))
    return list(result.scalars().all())
