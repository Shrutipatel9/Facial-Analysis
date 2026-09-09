"""Payment endpoints -- thin: all logic lives in app/services/payment_service.py.
See docs/api-specification.md §8.
"""

from fastapi import APIRouter, Depends, Header, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.payments import CheckoutResponse, PaymentOut, PaymentStatusOut
from app.services import payment_service

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> CheckoutResponse:
    checkout_url = await payment_service.create_checkout_session(db, user)
    return CheckoutResponse(checkout_url=checkout_url)


@router.get("/status", response_model=PaymentStatusOut)
async def get_payment_status(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> PaymentStatusOut:
    status_dict = await payment_service.get_status(db, user.id)
    return PaymentStatusOut.model_validate(status_dict)


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(..., alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db),
) -> Response:
    # Deliberately no get_current_user -- Stripe calls this, not our own
    # frontend. Trust is established entirely via the signature check
    # inside handle_webhook_event, never via a user session.
    payload = await request.body()
    await payment_service.handle_webhook_event(db, payload, stripe_signature)
    return Response(status_code=status.HTTP_200_OK)


@router.get("", response_model=list[PaymentOut])
async def list_payments(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[PaymentOut]:
    records = await payment_service.list_payments(db, user.id)
    return [PaymentOut.model_validate(record) for record in records]
