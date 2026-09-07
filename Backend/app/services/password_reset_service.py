"""Forgot-password / reset-password flow.

Reuses otp_service's request_otp (same cooldown/lockout mechanics,
purpose="password_reset" instead of "signup"/"login") and
verify_otp_by_email (the email-keyed verification path built specifically
for this flow, since there's no challenge_id round-trip -- see that
function's docstring), then adds the actual password update and a full
session wipe on success.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.exceptions import AccountLockedError, OTPCooldownError, SamePasswordError
from app.services import jwt_service, otp_service, user_service
from app.services.password_service import hash_new_password

PASSWORD_RESET_PURPOSE = "password_reset"


async def request_password_reset(db: AsyncSession, email: str) -> None:
    """Always succeeds from the caller's perspective -- the router returns
    the same generic message regardless of what happens here. Silently does
    nothing if the email doesn't correspond to a real account, so this can
    never be used to enumerate accounts.

    When the account DOES exist, this is subject to the exact same
    per-account cooldown/lockout as every other OTP request
    (otp_service.request_otp) -- but OTPCooldownError/AccountLockedError are
    deliberately swallowed here rather than left to propagate: letting a
    real account's cooldown/lockout surface as a 429 while a nonexistent
    email always returns 200 would itself be an enumeration signal (send
    the same request twice in a row and see whether you get a 429). The
    cooldown/lockout still function exactly as normal -- they just don't
    change what this endpoint reports back.
    """
    user = await user_service.get_by_email(db, email)
    if user is None:
        return
    try:
        await otp_service.request_otp(db, user, PASSWORD_RESET_PURPOSE)
    except (OTPCooldownError, AccountLockedError):
        pass


async def reset_password(db: AsyncSession, *, email: str, otp: str, new_password: str) -> None:
    """Verifies the code, rejects a no-op "reset" to the same password, and
    on success revokes every existing session for the account (not just the
    current one -- the old password may have been known to someone else,
    so every device must be forced to log in again, not just this one)."""
    user = await otp_service.verify_otp_by_email(db, email=email, purpose=PASSWORD_RESET_PURPOSE, code=otp)

    # Only reached after OTP verification already succeeded -- the caller
    # has proven access to the account by this point, so this check (and
    # its distinct error) is not an enumeration concern the way the OTP
    # verification errors above are.
    if verify_password(new_password, user.password_hash):
        raise SamePasswordError()

    user.password_hash = hash_new_password(new_password)
    await jwt_service.revoke_all_sessions_for_user(db, user.id)
