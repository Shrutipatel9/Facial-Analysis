"""FR-027 (Milestone 3) -- Care Team support requests. Pure email relay, no
persistence: the phase plan's own recommended default for a first pass at
low expected volume ("ship the UI entry point + a simple ticket/email
capture first, deferring live-chat infrastructure"). A SupportRequest
table can be added later without touching the API contract if volume
later warrants it.
"""

import uuid

from app.core.config import get_settings
from app.exceptions import EmailDeliveryError
from app.models.user import User
from app.services.email_service import get_email_sender


async def submit_support_request(user: User, subject: str, message: str, report_id: uuid.UUID | None) -> None:
    settings = get_settings()
    if not settings.support_email:
        raise EmailDeliveryError("Support email is not configured -- set SUPPORT_EMAIL in Backend/.env.")
    await get_email_sender().send_support_request_email(
        to_email=settings.support_email,
        from_user_email=user.email,
        subject=subject,
        message=message,
        report_id=str(report_id) if report_id else None,
    )
