"""Access + refresh token issuance, rotation, and revocation.

This is the single highest-risk module in the authentication feature --
see docs/authentication.md §4-5 and the reuse-detection notes below.
"""

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import create_access_token, generate_refresh_token, hash_refresh_token
from app.exceptions import RefreshTokenExpiredError, RefreshTokenInvalidError, RefreshTokenReuseError
from app.models.refresh_token import RefreshToken
from app.models.user import User


class TokenPair:
    __slots__ = ("access_token", "refresh_token", "expires_in", "user")

    def __init__(self, access_token: str, refresh_token: str, expires_in: int, user: User) -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_in = expires_in
        self.user = user


async def issue_token_pair(db: AsyncSession, user: User) -> TokenPair:
    """Issue a brand-new token pair, starting a new rotation family. Used
    only on successful OTP verification (WF-002 step 2) -- never as part of
    refresh, which rotates within the existing family instead."""
    settings = get_settings()
    now = datetime.now(UTC)

    raw_refresh_token = generate_refresh_token()
    record = RefreshToken(
        family_id=uuid.uuid4(),
        user_id=user.id,
        token_hash=hash_refresh_token(raw_refresh_token),
        expires_at=now + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(record)
    await db.flush()

    access_token = create_access_token(subject=str(user.id), role=user.role)
    return TokenPair(access_token, raw_refresh_token, settings.access_token_expire_minutes * 60, user)


async def rotate_refresh_token(
    db: AsyncSession,
    raw_refresh_token: str,
    *,
    _after_read_hook: Callable[[], Awaitable[None]] | None = None,
) -> TokenPair:
    """Exchange a valid refresh token for a new pair, rotating it.

    Reuse detection: if the token we were handed was already rotated out
    (its row's revoked_at is already set), that's evidence of theft -- the
    entire family is revoked and the caller must fully re-authenticate.
    This is distinct from a benign concurrent-refresh race (two requests
    racing to rotate the *same still-valid* token), which is handled by the
    atomic conditional UPDATE below: exactly one request wins the rotation,
    the other fails cleanly with RefreshTokenInvalidError -- it must NOT
    also trigger a family revocation, since both requests came from the
    legitimate client (e.g. two browser tabs), not an attacker.
    """
    settings = get_settings()
    now = datetime.now(UTC)
    token_hash = hash_refresh_token(raw_refresh_token)

    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    record = result.scalar_one_or_none()

    if record is None:
        raise RefreshTokenInvalidError()

    if record.revoked_at is not None:
        await _revoke_family(db, record.family_id, now)
        raise RefreshTokenReuseError()

    if record.expires_at < now:
        raise RefreshTokenExpiredError()

    if _after_read_hook is not None:
        # Test-only synchronization seam: lets integration tests force two
        # concurrent callers to both complete their initial read before
        # either attempts the atomic update below, deterministically
        # reproducing the race the update is designed to resolve. A no-op
        # in production (parameter is never passed).
        await _after_read_hook()

    # Atomic conditional revoke: only succeeds if no one else revoked this
    # exact row between our SELECT above and this UPDATE. Under Postgres's
    # default READ COMMITTED isolation, a concurrent UPDATE on the same row
    # blocks until the first commits, then re-evaluates this WHERE clause
    # against the now-committed (already-revoked) row and matches zero rows
    # -- so exactly one concurrent caller ever wins this race.
    claim_result = await db.execute(
        update(RefreshToken)
        .where(RefreshToken.id == record.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
        .returning(RefreshToken.id)
    )
    if claim_result.scalar_one_or_none() is None:
        # Lost the race. The winning request already rotated this token
        # legitimately -- do not revoke the family, just fail this request.
        raise RefreshTokenInvalidError()

    new_raw_refresh_token = generate_refresh_token()
    new_record = RefreshToken(
        family_id=record.family_id,
        user_id=record.user_id,
        token_hash=hash_refresh_token(new_raw_refresh_token),
        expires_at=now + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(new_record)
    await db.flush()

    await db.execute(update(RefreshToken).where(RefreshToken.id == record.id).values(replaced_by_id=new_record.id))

    user = await db.get(User, record.user_id)
    if user is None:
        # The user row was deleted after the token was issued -- treat as
        # an invalid session rather than crashing.
        raise RefreshTokenInvalidError()

    access_token = create_access_token(subject=str(user.id), role=user.role)
    return TokenPair(access_token, new_raw_refresh_token, settings.access_token_expire_minutes * 60, user)


async def revoke_current_session(db: AsyncSession, raw_refresh_token: str) -> None:
    """Logout: revokes only the single session tied to this refresh token,
    not the whole family/all devices (client_requirements.md's WF-002 says
    "revoke the refresh token", singular). Idempotent -- revoking an
    already-revoked or unknown token is not an error."""
    token_hash = hash_refresh_token(raw_refresh_token)
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == token_hash, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    await db.flush()


async def revoke_all_sessions_for_user(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Kills every active session (every family) for a user, not just one.

    Used after a password reset: the old password may have been known to
    someone else, so every existing refresh token -- on every device --
    must stop working, forcing a fresh login everywhere. This is a stronger
    action than logout (which only revokes the current session) or
    reuse-detection's family revoke (which only kills the one compromised
    lineage); a password reset is treated as "assume every existing session
    might be compromised."
    """
    await db.execute(
        update(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)).values(
            revoked_at=datetime.now(UTC)
        )
    )
    await db.flush()


async def _revoke_family(db: AsyncSession, family_id: uuid.UUID, now: datetime) -> None:
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    await db.flush()
