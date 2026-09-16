"""Test configuration.

Points the app at a dedicated `facial_analysis_test` database (same
Postgres instance as dev, different database -- see docker-compose.yml)
*before* any app module is imported, since app/db/session.py builds its
engine from Settings at import time. Also pins EMAIL_PROVIDER=console
regardless of the developer's local .env (which may have EMAIL_PROVIDER=smtp
for real local testing) -- tests must never depend on real SMTP credentials
existing, and use the email_sender fixture below to intercept sends anyway.

Same reasoning applies to IMAGE_GEN_API_KEY (BR-006: real image-gen API
calls must never run in automated tests): the ai-visuals/report-visual
integration tests rely on generation failing *fast* (a missing key short-
circuits in GeminiImageGenerationClient.__init__/OpenAIImageGenerationClient
.__init__ with no network call) to assert on settlement within a few
seconds -- they were never mocking the image-gen client boundary directly.
Before this override existed, a developer who added a real key to their
local .env (e.g. to manually verify AI Visuals in the browser) would
silently make the whole suite start issuing real, billed image-gen
requests the moment they next ran `pytest`, discovered only via these two
tests timing out against the live API's actual latency.

AI_API_KEY is blanked here too (2026-09-17) -- not because narrative-
generation tests need it blank (they monkeypatch ai_narrative_service.
get_ai_client() directly via the `ai_recorder` fixture, which never
touches Settings.ai_api_key at all), but because Settings.
_default_image_gen_api_key (app/core/config.py) now falls back
IMAGE_GEN_API_KEY to AI_API_KEY when the former is unset -- leaving
AI_API_KEY as the developer's real key would silently re-open the exact
image-gen hole the IMAGE_GEN_API_KEY override above exists to close.
"""

import json
import os
from types import SimpleNamespace

os.environ["DATABASE_URL"] = "postgresql+asyncpg://facial_analysis:facial_analysis@localhost:5433/facial_analysis_test"
os.environ["EMAIL_PROVIDER"] = "console"
os.environ["AI_API_KEY"] = ""
os.environ["IMAGE_GEN_API_KEY"] = ""
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
from app.services.ai_narrative_service import _FEATURE_SUBSECTIONS
from app.services.facial_measurement_service import ANALYSIS_FEATURES

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


def _fake_completion_response() -> SimpleNamespace:
    """A minimal fake OpenAI-shaped chat-completion response carrying a
    valid narrative JSON body -- shared by every test that needs a
    successful ai_narrative_service.generate_narrative() call without a
    real OpenAI request. `sections` headings are built from the real
    _FEATURE_SUBSECTIONS vocabulary (not hardcoded strings here) so this
    fixture can't silently drift out of sync with it."""
    content = json.dumps(
        {
            "features": {
                feature: {
                    "sections": {heading: f"{heading} for {feature}." for heading in _FEATURE_SUBSECTIONS[feature]},
                    "summary_callout": feature,
                    "strengths": "Looks natural.",
                    "areas_of_note": "None notable.",
                    "recommendation_ideas": ["Use a daily moisturizer."],
                }
                for feature in ANALYSIS_FEATURES
            },
            "closing_recommendations": "Consider seeing a dermatologist for a full assessment.",
        }
    )
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


_FAKE_STREAM_CHUNKS: tuple[str, ...] = (
    "Based on your report, ",
    "here's a **general tip**: ",
    "stay consistent with your routine.",
)


class _FakeStream:
    """A minimal fake of openai's AsyncStream[ChatCompletionChunk] -- just
    enough to support `async for chunk in stream: chunk.choices[0].delta.content`,
    matching chat_service.stream_reply's exact consumption shape."""

    def __init__(self, pieces: tuple[str, ...]) -> None:
        self._pieces = pieces

    def __aiter__(self):
        return self._generate()

    async def _generate(self):
        for piece in self._pieces:
            yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=piece))])


class AiRecorder:
    """Call counter for the fake AI client below -- lets a test assert a
    refused chat question (chat_refusal_keywords.is_medical_question)
    triggered zero provider calls (BR-006), not just that the response
    text looked right."""

    def __init__(self) -> None:
        self.call_count = 0


@pytest.fixture
def ai_recorder(monkeypatch) -> AiRecorder:
    """Monkeypatches ai_narrative_service.get_ai_client() to a fake client
    used by any integration test that needs a completed analysis
    (report_flow, ai_visuals_flow, chat_flow, ...) without a real AI
    provider call. A module-level conftest fixture (not defined per test
    file) since it's shared by more than one -- pytest resolves it by name
    with no import needed.

    `create()` branches on `stream=True` (chat_service.stream_reply's call
    shape) vs the default non-streaming shape (ai_narrative_service.
    generate_narrative's call shape) so one fixture serves both callers."""
    recorder = AiRecorder()

    async def create(**kwargs):
        recorder.call_count += 1
        if kwargs.get("stream"):
            return _FakeStream(_FAKE_STREAM_CHUNKS)
        return _fake_completion_response()

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr("app.services.ai_narrative_service.get_ai_client", lambda: fake_client)
    return recorder
