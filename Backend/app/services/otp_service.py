"""OTP challenge lifecycle: create, resend, verify.

Cooldown and lockout are enforced here, uniformly, regardless of which
endpoint (register/login/resend) is asking for a new code -- so "duplicate
signup while the first OTP is still on cooldown" and "resend clicked twice"
are the same code path, not two separate implementations that could drift.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import generate_otp_code, hash_otp_code, verify_otp_code
from app.exceptions import (
    AccountLockedError,
    OTPChallengeNotFoundError,
    OTPCooldownError,
    OTPExpiredError,
    OTPInvalidError,
)
from app.models.otp_record import OTPRecord
from app.models.user import User
from app.services import user_service
from app.services.email_service import get_email_sender


def _seconds_until(target: datetime, now: datetime) -> int:
    return max(1, int((target - now).total_seconds()))


def _ensure_not_locked(user: User, now: datetime) -> None:
    if user.otp_locked_until is not None and user.otp_locked_until > now:
        raise AccountLockedError(retry_after_seconds=_seconds_until(user.otp_locked_until, now))


async def _latest_otp_record(db: AsyncSession, user_id: uuid.UUID) -> OTPRecord | None:
    result = await db.execute(
        select(OTPRecord).where(OTPRecord.user_id == user_id).order_by(OTPRecord.created_at.desc()).limit(1)
    )
    return result.scalar_one_or_none()


async def request_otp(db: AsyncSession, user: User, purpose: str) -> OTPRecord:
    """Create a new OTP challenge, superseding any prior one for this user.

    Used by register, login, and resend alike -- see module docstring.
    """
    settings = get_settings()
    now = datetime.now(UTC)

    _ensure_not_locked(user, now)

    # Cooldown only applies against a still-*outstanding* challenge (not yet
    # consumed): it exists to stop rapid re-requesting of a challenge the
    # user hasn't finished with, not to throttle an unrelated, later,
    # legitimate request (e.g. logging in shortly after finishing signup --
    # that OTP was already consumed by a successful verify, so it must not
    # block issuing a fresh one for the new action).
    last = await _latest_otp_record(db, user.id)
    if last is not None and not last.consumed:
        cooldown_ends_at = last.created_at + timedelta(seconds=settings.otp_resend_cooldown_seconds)
        if cooldown_ends_at > now:
            raise OTPCooldownError(retry_after_seconds=_seconds_until(cooldown_ends_at, now))
        last.consumed = True  # superseded by the new one below

    code = generate_otp_code()
    record = OTPRecord(
        user_id=user.id,
        purpose=purpose,
        otp_hash=hash_otp_code(code),
        expires_at=now + timedelta(minutes=settings.otp_expire_minutes),
    )
    db.add(record)
    await db.flush()

    try:
        await get_email_sender().send_otp_email(to_email=user.email, otp_code=code, purpose=purpose)
    except Exception:
        # Do not leave a challenge the user can never satisfy (they never
        # received the code) masquerading as active -- but the cooldown
        # timer above still applies to the next attempt, so this doesn't
        # become a way to hammer the email provider.
        record.consumed = True
        await db.flush()
        raise

    return record


async def resend_otp(db: AsyncSession, challenge_id: str) -> OTPRecord:
    record, user = await _get_record_and_user(db, challenge_id)

    # Lockout must be checked before the "is this record still live" check
    # below: a user's 5th failed attempt marks *that* record consumed as a
    # side effect of locking them out, and a locked-out user retrying
    # resend/verify must still see AccountLockedError, not a generic
    # "challenge not found" that hides the real reason.
    _ensure_not_locked(user, datetime.now(UTC))

    if record.consumed:
        raise OTPChallengeNotFoundError()

    return await request_otp(db, user, record.purpose)


async def verify_otp(db: AsyncSession, challenge_id: str, code: str) -> User:
    record, user = await _get_record_and_user(db, challenge_id)

    now = datetime.now(UTC)
    _ensure_not_locked(user, now)  # see resend_otp's comment on ordering

    if record.consumed:
        raise OTPChallengeNotFoundError()

    if record.expires_at < now:
        # Expired, not wrong -- does not count as a failed attempt.
        raise OTPExpiredError()

    await _validate_code_and_consume(db, record, user, code, now)
    return user


async def verify_otp_by_email(db: AsyncSession, *, email: str, purpose: str, code: str) -> User:
    """Password-reset (and any future email-driven, non-challenge_id) OTP
    verification.

    Unlike verify_otp, there's no challenge_id round-trip: the forgot-
    password request never hands back an identifying token (see
    password_reset_service.py, which deliberately never reveals whether an
    account exists), so this looks up the user's current OTP by email +
    purpose instead.

    Every failure path before the lockout/expiry checks collapses to the
    SAME OTPInvalidError, deliberately: a nonexistent email, an existing
    email with no pending reset, and a genuinely wrong code must all look
    identical to the caller (anti-enumeration). Only OTPExpiredError is
    allowed to differ, since reaching it already requires a real, matching
    challenge to exist.
    """
    normalized = email.strip().lower()
    user = await user_service.get_by_email(db, normalized)
    if user is None:
        # Burn roughly the same time a real lookup+compare would, so the
        # response time doesn't itself signal "no such account".
        verify_otp_code(code, hash_otp_code("000000"))
        raise OTPInvalidError()

    now = datetime.now(UTC)
    _ensure_not_locked(user, now)

    record = await _latest_otp_record(db, user.id)
    if record is None or record.consumed or record.purpose != purpose:
        raise OTPInvalidError()

    if record.expires_at < now:
        raise OTPExpiredError()

    await _validate_code_and_consume(db, record, user, code, now)
    return user


async def _validate_code_and_consume(
    db: AsyncSession, record: OTPRecord, user: User, code: str, now: datetime
) -> None:
    """Assumes the caller already confirmed the record is live (not
    consumed) and not expired. Raises OTPInvalidError, or AccountLockedError
    on the attempt that trips the lockout threshold; marks the record
    consumed on a correct code."""
    if not verify_otp_code(code, record.otp_hash):
        settings = get_settings()
        record.attempt_count += 1
        if record.attempt_count >= settings.otp_max_attempts:
            user.otp_locked_until = now + timedelta(minutes=settings.otp_lockout_minutes)
            record.consumed = True
            await db.flush()
            # The attempt that *triggers* the lock should itself report the
            # lock, not "wrong code" -- the caller needs to know to stop
            # retrying and see the retry_after_seconds, not assume one more
            # attempt might work.
            raise AccountLockedError(retry_after_seconds=_seconds_until(user.otp_locked_until, now))
        await db.flush()
        raise OTPInvalidError()

    record.consumed = True
    await db.flush()


async def _get_record_and_user(db: AsyncSession, challenge_id: str) -> tuple[OTPRecord, User]:
    try:
        record_id = uuid.UUID(challenge_id)
    except ValueError as exc:
        raise OTPChallengeNotFoundError() from exc

    record = await db.get(OTPRecord, record_id)
    if record is None:
        raise OTPChallengeNotFoundError()

    user = await db.get(User, record.user_id)
    if user is None:
        raise OTPChallengeNotFoundError()

    return record, user
