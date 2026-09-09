"""Test configuration.

Points the app at a dedicated `facial_analysis_test` database (same
Postgres instance as dev, different database -- see docker-compose.yml)
*before* any app module is imported, since app/db/session.py builds its
engine from Settings at import time. Also pins EMAIL_PROVIDER=console
regardless of the developer's local .env (which may have EMAIL_PROVIDER=smtp
for real local testing) -- tests must never depend on real SMTP credentials
existing, and use the email_sender fixture below to intercept sends anyway.
"""

import os

os.environ["DATABASE_URL"] = "postgresql+asyncpg://facial_analysis:facial_analysis@localhost:5433/facial_analysis_test"
os.environ["EMAIL_PROVIDER"] = "console"
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
# Regardless of the developer's local .env (same posture as EMAIL_PROVIDER
# above) -- "database" is also the real default now, so tests exercise the
# actual DatabasePhotoStorage implementation, not a dev-only local-disk
# stand-in. No filesystem isolation needed: it's already isolated by the
# dedicated test database, and _clean_tables below wipes photo_blobs like
# every other table.
os.environ["PHOTO_STORAGE_PROVIDER"] = "database"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

import app.models  # noqa: F401  -- registers models on Base.metadata
from app.core.rate_limit import limiter
from app.db.base import Base
from app.db.session import async_session_factory, engine

# Cookie-authenticated endpoints require these (app/core/csrf.py).
_CSRF_HEADERS = {
    "Origin": "http://localhost:3000",
    "X-Requested-With": "XMLHttpRequest",
}


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _test_schema():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    # Endpoints are decorated with @limiter.limit(...) (app/core/rate_limit.py);
    # without a reset, the limiter's in-memory counters would carry over
    # between tests in the same process and cause unrelated tests to fail
    # with 429s.
    limiter.reset()
    yield


@pytest_asyncio.fixture(autouse=True)
async def _clean_tables():
    yield
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    """A session for tests that call service functions directly.

    Auto-commits so writes are visible to a second session opened within
    the same test (e.g. the HTTP client fixture below), matching how the
    app's own get_db behaves in production.
    """
    async with async_session_factory() as session:
        yield session
        await session.commit()


@pytest_asyncio.fixture
async def client():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers=_CSRF_HEADERS,
    ) as ac:
        yield ac


class RecordingEmailSender:
    """Test double: records the most recently "sent" OTP per recipient
    instead of actually sending email, so tests can read the code without
    scraping logs. OTPs are never stored in plaintext in the database
    (only their hash) -- this is the one place in the test suite that ever
    sees a real code."""

    def __init__(self) -> None:
        self.sent: dict[str, str] = {}

    async def send_otp_email(self, *, to_email: str, otp_code: str, purpose: str) -> None:
        self.sent[to_email] = otp_code


@pytest.fixture(autouse=True)
def email_sender(monkeypatch) -> RecordingEmailSender:
    recorder = RecordingEmailSender()
    monkeypatch.setattr("app.services.otp_service.get_email_sender", lambda: recorder)
    return recorder
