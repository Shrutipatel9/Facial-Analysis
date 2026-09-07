"""OTP email delivery, behind a swappable interface.

The client confirmed the delivery *channel* is email (NFR-012) but left the
*vendor* (SendGrid/SES/Postmark/etc.) open, non-blocking. Isolating it
behind EmailSender means picking a real vendor later is a new implementation
of this interface, not a rewrite of otp_service.py.
"""

import asyncio
import logging
import smtplib
from abc import ABC, abstractmethod
from email.message import EmailMessage
from functools import lru_cache

from app.core.config import get_settings
from app.exceptions import EmailDeliveryError

logger = logging.getLogger(__name__)

_PURPOSE_COPY = {
    "signup": "finish creating your account",
    "login": "sign in",
}


class EmailSender(ABC):
    @abstractmethod
    async def send_otp_email(self, *, to_email: str, otp_code: str, purpose: str) -> None:
        """Raise EmailDeliveryError on failure -- callers must not report a
        successful send to the client when this raises."""


class ConsoleEmailSender(EmailSender):
    """Development-only sender: logs the OTP instead of sending real email.

    Never used when EMAIL_PROVIDER is anything other than "console" -- see
    get_email_sender(). This intentionally makes the OTP visible in server
    logs for local development/testing; it must never be selected in a
    production configuration.
    """

    async def send_otp_email(self, *, to_email: str, otp_code: str, purpose: str) -> None:
        logger.info("[dev email] OTP for %s (%s): %s", to_email, purpose, otp_code)


def _build_otp_message(*, from_addr: str, to_email: str, otp_code: str, purpose: str) -> EmailMessage:
    action = _PURPOSE_COPY.get(purpose, "continue")
    settings = get_settings()

    message = EmailMessage()
    message["Subject"] = f"Your verification code is {otp_code}"
    message["From"] = from_addr
    message["To"] = to_email
    message.set_content(
        f"""Your verification code is: {otp_code}

Enter this code to {action}. It expires in {settings.otp_expire_minutes} minutes
and can only be used once.

If you didn't request this, you can safely ignore this email.

-- Facial Analysis"""
    )
    return message


class SmtpEmailSender(EmailSender):
    """Sends real email over SMTP with STARTTLS (e.g. Gmail: smtp.gmail.com:587).

    smtplib is synchronous; the actual send runs in a worker thread via
    asyncio.to_thread so it doesn't block the event loop that's serving
    every other concurrent request.
    """

    async def send_otp_email(self, *, to_email: str, otp_code: str, purpose: str) -> None:
        settings = get_settings()
        message = _build_otp_message(
            from_addr=settings.email_from,  # type: ignore[arg-type]  # guaranteed non-None when provider=smtp
            to_email=to_email,
            otp_code=otp_code,
            purpose=purpose,
        )
        try:
            await asyncio.to_thread(self._send_sync, message)
        except (smtplib.SMTPException, OSError) as exc:
            logger.exception("SMTP send failed for purpose=%s", purpose)
            raise EmailDeliveryError("Failed to send verification email.") from exc

    def _send_sync(self, message: EmailMessage) -> None:
        settings = get_settings()
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:  # type: ignore[arg-type]
            server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)  # type: ignore[arg-type]
            server.send_message(message)


@lru_cache
def get_email_sender() -> EmailSender:
    settings = get_settings()
    if settings.email_provider == "console":
        return ConsoleEmailSender()
    if settings.email_provider == "smtp":
        return SmtpEmailSender()
    raise EmailDeliveryError(f"Unsupported EMAIL_PROVIDER: {settings.email_provider!r}")
