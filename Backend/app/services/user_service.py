import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.password_service import hash_new_password


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    normalized = email.strip().lower()
    result = await db.execute(select(User).where(User.email == normalized))
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await db.get(User, user_id)


async def create_pending_user(db: AsyncSession, *, email: str, password: str) -> User:
    """Create a new, unverified user for signup Step 1.

    Callers must have already confirmed no *verified* account exists for
    this email (EmailAlreadyVerifiedError) -- this function does not check.
    """
    user = User(
        email=email.strip().lower(),
        password_hash=hash_new_password(password),
        verification_status="pending",
    )
    db.add(user)
    await db.flush()
    return user


async def restart_pending_signup(db: AsyncSession, user: User, *, password: str) -> User:
    """A signup retry against an email that's registered-but-unverified
    (docs/testing-strategy.md edge case): update the password (the user may
    have mistyped it the first time) and let the caller regenerate an OTP,
    rather than erroring or silently ignoring the new password.
    """
    user.password_hash = hash_new_password(password)
    await db.flush()
    return user


async def mark_verified(db: AsyncSession, user: User) -> None:
    user.verification_status = "verified"
    await db.flush()
