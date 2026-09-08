"""Forgot-password / reset-password flow.

Three-step shape: request (email-only, always generic) -> verify
(email+OTP -> short-lived reset_token) -> reset (reset_token+new_password).
The verify step reuses otp_service.verify_otp_by_email unchanged (the
email-keyed verification path built specifically for this flow, since
there's no challenge_id round-trip -- see that function's docstring); the
reset step no longer touches OTP at all -- it trusts reset_token, a
purpose-scoped JWT (app/core/security.py's create_purpose_token) bound to a
fingerprint of the user's current password hash so it self-invalidates the
instant a reset actually completes (single-use, no DB table needed).
"""

import uuid
from datetime import timedelta
from typing import Any

import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import create_purpose_token, decode_access_token, hash_reset_binding, verify_password
from app.exceptions import (
    AccountLockedError,
    OTPCooldownError,
    ResetTokenInvalidError,
    SamePasswordError,
    WeakPasswordError,
)
from app.models.user import User
from app.services import jwt_service, otp_service, user_service
from app.services.password_service import hash_new_password, validate_password_strength

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


async def verify_reset_otp(db: AsyncSession, *, email: str, otp: str) -> tuple[str, int]:
    """Verifies the code (reuses otp_service.verify_otp_by_email -- same
    anti-enumeration/lockout semantics as before), then mints a short-lived
    reset_token proving that verification succeeded. Returns
    (reset_token, expires_in_seconds)."""
    user = await otp_service.verify_otp_by_email(db, email=email, purpose=PASSWORD_RESET_PURPOSE, code=otp)

    settings = get_settings()
    ttl = timedelta(minutes=settings.otp_expire_minutes)
    reset_token = create_purpose_token(
        subject=str(user.id),
        purpose=PASSWORD_RESET_PURPOSE,
        expires_delta=ttl,
        pwd_fp=hash_reset_binding(user.password_hash),
    )
    return reset_token, int(ttl.total_seconds())


async def reset_password(db: AsyncSession, *, reset_token: str, new_password: str) -> None:
    """Decodes/validates reset_token (raises ResetTokenInvalidError for any
    malformed/expired/wrong-purpose/already-redeemed case -- see
    _resolve_reset_token), rejects a no-op "reset" to the same password, and
    on success revokes every existing session for the account (not just the
    current one -- the old password may have been known to someone else, so
    every device must be forced to log in again, not just this one)."""
    user = await _resolve_reset_token(db, reset_token)

    try:
        validate_password_strength(new_password, user.email)
    except ValueError as exc:
        raise WeakPasswordError(str(exc)) from exc

    # Only reached after reset_token verification already succeeded -- the
    # caller has proven access to the account by this point, so this check
    # (and its distinct error) is not an enumeration concern.
    if verify_password(new_password, user.password_hash):
        raise SamePasswordError()

    user.password_hash = hash_new_password(new_password)
    await jwt_service.revoke_all_sessions_for_user(db, user.id)


async def _resolve_reset_token(db: AsyncSession, reset_token: str) -> User:
    try:
        payload: dict[str, Any] = decode_access_token(reset_token)
    except jwt.InvalidTokenError as exc:
        raise ResetTokenInvalidError() from exc

    if payload.get("purpose") != PASSWORD_RESET_PURPOSE:
        raise ResetTokenInvalidError()

    try:
        user_id = uuid.UUID(payload.get("sub", ""))
    except ValueError as exc:
        raise ResetTokenInvalidError() from exc

    user = await user_service.get_by_id(db, user_id)
    if user is None:
        raise ResetTokenInvalidError()

    if payload.get("pwd_fp") != hash_reset_binding(user.password_hash):
        # Wrong fingerprint = tampered, or (far more likely) the password
        # already changed since this token was minted -- i.e. reuse.
        raise ResetTokenInvalidError()

    return user
