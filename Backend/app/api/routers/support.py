"""Care Team support endpoints (FR-027) -- thin: all logic lives in
app/services/support_service.py.
"""

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_current_user
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.support import SupportRequestCreate
from app.services import support_service

router = APIRouter(prefix="/support", tags=["support"])


@router.post("/requests", response_model=MessageResponse)
@limiter.limit("5/minute")
async def submit_support_request(
    request: Request,
    payload: SupportRequestCreate,
    user: User = Depends(get_current_user),
) -> MessageResponse:
    await support_service.submit_support_request(user, payload.subject, payload.message, payload.report_id)
    return MessageResponse(message="Your request has been sent. Our team will follow up by email.")
