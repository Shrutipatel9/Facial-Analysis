from types import SimpleNamespace

import pytest

from app.services.image_generation_service import (
    ImageGenerationClient,
    ImageGenerationError,
    _classify_api_error,
    _extract_inline_image,
    generate_with_retry,
)


class _FakeClient(ImageGenerationClient):
    """A minimal in-memory ImageGenerationClient for testing
    generate_with_retry's policy without touching the real google.genai
    SDK -- same "fake at the ABC boundary" convention this project already
    uses for ai_narrative_service's AsyncOpenAI client in integration
    tests, just at the interface level since a real ABC exists here."""

    def __init__(self, outcomes: list[bytes | ImageGenerationError]) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[tuple[bytes, str]] = []

    async def generate_before_after(self, *, source_image: bytes, prompt: str) -> bytes:
        self.calls.append((source_image, prompt))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, ImageGenerationError):
            raise outcome
        return outcome


class TestGenerateWithRetry:
    async def test_succeeds_on_first_attempt_without_retrying(self):
        client = _FakeClient([b"generated-image-bytes"])
        result = await generate_with_retry(client, source_image=b"source", prompt="a prompt", max_retries=2)
        assert result == b"generated-image-bytes"
        assert len(client.calls) == 1

    async def test_retries_a_retryable_failure_then_succeeds(self):
        client = _FakeClient(
            [
                ImageGenerationError("timed out", reason="timeout", retryable=True),
                b"generated-on-second-try",
            ]
        )
        result = await generate_with_retry(client, source_image=b"source", prompt="a prompt", max_retries=2)
        assert result == b"generated-on-second-try"
        assert len(client.calls) == 2

    async def test_exhausts_retries_and_raises_the_last_error(self):
        client = _FakeClient(
            [
                ImageGenerationError("rate limited 1", reason="rate_limited", retryable=True),
                ImageGenerationError("rate limited 2", reason="rate_limited", retryable=True),
                ImageGenerationError("rate limited 3", reason="rate_limited", retryable=True),
            ]
        )
        with pytest.raises(ImageGenerationError) as excinfo:
            await generate_with_retry(client, source_image=b"source", prompt="a prompt", max_retries=2)
        assert excinfo.value.reason == "rate_limited"
        assert len(client.calls) == 3  # initial attempt + 2 retries

    async def test_never_retries_a_content_policy_refusal(self):
        """BR-006 cost control: a permanent refusal must not burn
        additional spend retrying it."""
        client = _FakeClient(
            [
                ImageGenerationError("refused", reason="content_policy_refusal", retryable=False),
                b"should never be reached",
            ]
        )
        with pytest.raises(ImageGenerationError) as excinfo:
            await generate_with_retry(client, source_image=b"source", prompt="a prompt", max_retries=2)
        assert excinfo.value.reason == "content_policy_refusal"
        assert len(client.calls) == 1  # no retry attempted

    async def test_zero_max_retries_still_attempts_once(self):
        client = _FakeClient([b"generated"])
        result = await generate_with_retry(client, source_image=b"source", prompt="a prompt", max_retries=0)
        assert result == b"generated"
        assert len(client.calls) == 1


def _fake_response(*, finish_reason: str = "STOP", inline_data: bytes | None = b"png-bytes") -> SimpleNamespace:
    part = SimpleNamespace(inline_data=SimpleNamespace(data=inline_data) if inline_data is not None else None)
    content = SimpleNamespace(parts=[part])
    candidate = SimpleNamespace(finish_reason=finish_reason, content=content)
    return SimpleNamespace(candidates=[candidate])


class TestExtractInlineImage:
    def test_extracts_bytes_from_a_successful_response(self):
        response = _fake_response(finish_reason="STOP", inline_data=b"the-generated-png")
        assert _extract_inline_image(response) == b"the-generated-png"

    def test_returns_none_for_a_safety_refusal(self):
        response = _fake_response(finish_reason="SAFETY", inline_data=None)
        assert _extract_inline_image(response) is None

    def test_returns_none_for_prohibited_content(self):
        response = _fake_response(finish_reason="IMAGE_PROHIBITED_CONTENT", inline_data=None)
        assert _extract_inline_image(response) is None

    def test_returns_none_when_no_candidates(self):
        response = SimpleNamespace(candidates=[])
        assert _extract_inline_image(response) is None

    def test_returns_none_when_no_content_parts(self):
        candidate = SimpleNamespace(finish_reason="STOP", content=SimpleNamespace(parts=[]))
        response = SimpleNamespace(candidates=[candidate])
        assert _extract_inline_image(response) is None

    def test_returns_none_when_part_has_no_inline_data(self):
        response = _fake_response(finish_reason="STOP", inline_data=None)
        assert _extract_inline_image(response) is None


class _FakeApiError:
    def __init__(self, code: int) -> None:
        self.code = code


class TestClassifyApiError:
    def test_429_is_rate_limited_and_retryable(self):
        reason, retryable = _classify_api_error(_FakeApiError(429))  # type: ignore[arg-type]
        assert reason == "rate_limited"
        assert retryable is True

    def test_504_is_timeout_and_retryable(self):
        reason, retryable = _classify_api_error(_FakeApiError(504))  # type: ignore[arg-type]
        assert reason == "timeout"
        assert retryable is True

    def test_400_is_content_policy_refusal_and_not_retryable(self):
        reason, retryable = _classify_api_error(_FakeApiError(400))  # type: ignore[arg-type]
        assert reason == "content_policy_refusal"
        assert retryable is False

    def test_unrecognized_code_is_unknown_and_not_retryable(self):
        reason, retryable = _classify_api_error(_FakeApiError(500))  # type: ignore[arg-type]
        assert reason == "unknown"
        assert retryable is False
