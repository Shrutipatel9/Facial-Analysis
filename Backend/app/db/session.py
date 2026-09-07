"""Async SQLAlchemy engine/session setup and the get_db FastAPI dependency."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.exceptions import DomainError

settings = get_settings()

engine = create_async_engine(settings.database_url, pool_pre_ping=True)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yields a session that commits on a clean request, and ALSO commits
    when a DomainError (app/exceptions.py) propagates -- a DomainError is an
    *expected* business outcome (wrong password, OTP reuse, lockout, ...),
    not a failure of the write itself, and several of them are raised
    deliberately *after* a side effect that must survive the error response:
    incrementing an OTP attempt counter, setting a lockout, or revoking an
    entire refresh-token family on reuse detection. Rolling those back would
    silently undo the very security response they exist to produce.

    Only a *non*-DomainError exception (a bug, a DB error, anything
    unexpected) rolls back, to avoid persisting a half-applied write.
    """
    async with async_session_factory() as session:
        try:
            yield session
        except DomainError:
            await session.commit()
            raise
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit()
