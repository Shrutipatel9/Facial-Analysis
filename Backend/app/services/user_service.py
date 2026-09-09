import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import CurrentPasswordIncorrectError, SamePasswordError, WeakPasswordError
from app.models.user import User
from app.services.password_service import hash_new_password, validate_password_strength, verify_login_password


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    normalized = email.strip().lower()
    result = await db.execute(select(User).where(User.email == normalized))
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await db.get(User, user_id)


async def create_pending_user(db: AsyncSession, *, email: str, password: str, full_name: str) -> User:
    """Create a new, unverified user for signup Step 1.

    Callers must have already confirmed no *verified* account exists for
    this email (EmailAlreadyVerifiedError) -- this function does not check.
    """
    user = User(
        email=email.strip().lower(),
        password_hash=hash_new_password(password),
        full_name=full_name.strip(),
        verification_status="pending",
    )
    db.add(user)
    await db.flush()
    return user


async def restart_pending_signup(db: AsyncSession, user: User, *, password: str, full_name: str) -> User:
    """A signup retry against an email that's registered-but-unverified
    (docs/testing-strategy.md edge case): update the password (the user may
    have mistyped it the first time) and let the caller regenerate an OTP,
    rather than erroring or silently ignoring the new password. Also
    refreshes full_name in case they corrected a typo on retry.
    """
    user.password_hash = hash_new_password(password)
    user.full_name = full_name.strip()
    await db.flush()
    return user


async def mark_verified(db: AsyncSession, user: User) -> None:
    user.verification_status = "verified"
    await db.flush()


async def change_password(db: AsyncSession, user: User, *, current_password: str, new_password: str) -> None:
    """In-app, currently-authenticated password change -- proves identity
    via the current password rather than an emailed OTP. Deliberately does
    NOT revoke the caller's own session afterward (contrast
    password_reset_service.reset_password, which revokes every session
    since a forgot-password flow can't assume the requester still holds a
    valid one) -- FR-017's profile management explicitly should not sign
    the user out just for changing their password.
    """
    if not verify_login_password(current_password, user.password_hash):
        raise CurrentPasswordIncorrectError()

    try:
        validate_password_strength(new_password, user.email)
    except ValueError as exc:
        raise WeakPasswordError(str(exc)) from exc

    if verify_login_password(new_password, user.password_hash):
        raise SamePasswordError()

    user.password_hash = hash_new_password(new_password)
    await db.flush()
