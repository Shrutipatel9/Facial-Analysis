"""AI image generation (FR-022, Milestone 2) -- turns a per-feature photo
crop plus a text prompt into an AI-generated "after" image for the report's
before/after visualization.

ASM-011: vendor was Google Gemini 2.5 Flash Image, user-confirmed
2026-09-11 (see docs/client_requirements.md) -- blocked all along by a
zero-quota free-tier key. Switched to OpenAI (gpt-image-1) 2026-09-16 once
a billed OpenAI key was supplied (see OpenAIImageGenerationClient below).
Unlike app/services/ai_narrative_service.py's provider swap, neither of
these is a config-only change -- DeepSeek/OpenAI happen to share an
OpenAI-Chat-Completions-shaped API, so that module can just point the
`openai` SDK at a different base_url, but Gemini's image-generation call
shape (`contents=[...]`, `response_modalities=["IMAGE"]`, inline-data image
parts in the response) and OpenAI's `images.edit` call shape are each
genuinely different from one another -- a real ImageGenerationClient ABC
exists here instead, mirroring PhotoStorage's precedent (a real interface,
not a config trick), so this second implementation is exactly the vendor
swap that seam was built for.

Cost control (BR-006): retries only cover transient failures (timeout,
rate-limited) with backoff, via generate_with_retry() below. A permanent
refusal (safety/content-policy) is never retried -- retrying a permanent
refusal is exactly the kind of uncontrolled repeat spend BR-006 warns
about. Real provider calls never run in automated tests -- see
tests/unit/test_image_generation_service.py, which mocks each client's SDK
boundary exclusively (google.genai for Gemini, openai for OpenAI).
"""

import asyncio
import base64
import io
from abc import ABC, abstractmethod
from functools import lru_cache

from google.genai import types
from google.genai.errors import APIError
from openai import APITimeoutError, AsyncOpenAI, BadRequestError, OpenAIError, PermissionDeniedError, RateLimitError

from app.core.config import get_settings

# Gemini finish reasons that mean "a request completed without throwing,
# but produced no usable image" -- all permanent/non-retryable outcomes,
# not a transient failure. See google.genai.types.FinishReason.
_REFUSAL_FINISH_REASONS = frozenset(
    {
        "SAFETY",
        "PROHIBITED_CONTENT",
        "IMAGE_SAFETY",
        "IMAGE_PROHIBITED_CONTENT",
        "RECITATION",
        "IMAGE_RECITATION",
        "NO_IMAGE",
        "BLOCKLIST",
        "SPII",
    }
)

_RETRY_BACKOFF_SECONDS: tuple[float, ...] = (2.0, 8.0, 20.0)

# Shared verbatim by every caller of generate_before_after (report_visual_service.py,
# ai_visual_service.py) -- this exact safety/legal-disclaimer wording must not drift
# between call sites, so it lives here rather than being duplicated per caller.
IDENTITY_PRESERVATION_INSTRUCTION = (
    "Preserve the same person's identity, facial structure, lighting, and background exactly -- "
    "change only what the suggestion describes. This is an illustrative, non-clinical "
    "visualization, not a medical result or guaranteed outcome."
)


class ImageGenerationError(Exception):
    """Raised by any ImageGenerationClient implementation. `reason` drives
    both the retry policy (generate_with_retry) and the `error_reason`
    persisted on ReportFeatureVisual for support/debugging."""

    def __init__(self, message: str, *, reason: str, retryable: bool) -> None:
        # "timeout" | "rate_limited" | "content_policy_refusal" | "unknown"
        self.reason = reason
        self.retryable = retryable
        super().__init__(message)


class ImageGenerationClient(ABC):
    @abstractmethod
    async def generate_before_after(self, *, source_image: bytes, prompt: str) -> bytes:
        """`source_image` is a JPEG crop of one report feature (see
        facial_measurement_service.extract_feature_crops); `prompt`
        describes the desired edit plus an identity-preservation
        instruction (see report_visual_service.py's prompt construction).
        Returns the generated image's raw bytes, or raises
        ImageGenerationError -- never returns None/empty bytes silently."""


class GeminiImageGenerationClient(ImageGenerationClient):
    def __init__(self) -> None:
        # Lazy import mirrors S3PhotoStorage's own boto3-import pattern --
        # this dependency should only ever load when Gemini is actually
        # the configured provider, not on every app startup.
        from google import genai  # noqa: PLC0415

        settings = get_settings()
        if not settings.openai_api_key:
            raise ImageGenerationError(
                "OPENAI_API_KEY is not configured -- add a real key to Backend/.env before "
                "triggering visual generation.",
                reason="unknown",
                retryable=False,
            )
        self._client = genai.Client(api_key=settings.openai_api_key)
        self._model = settings.image_gen_model
        self._timeout = settings.image_gen_request_timeout_seconds

    async def generate_before_after(self, *, source_image: bytes, prompt: str) -> bytes:
        contents: list[str | types.Part] = [
            prompt,
            types.Part.from_bytes(data=source_image, mime_type="image/jpeg"),
        ]
        try:
            response = await asyncio.wait_for(
                self._client.aio.models.generate_content(
                    model=self._model,
                    contents=contents,  # type: ignore[arg-type]
                    config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
                ),
                timeout=self._timeout,
            )
        except TimeoutError as exc:
            raise ImageGenerationError("Gemini request timed out.", reason="timeout", retryable=True) from exc
        except APIError as exc:
            reason, retryable = _classify_api_error(exc)
            raise ImageGenerationError(str(exc), reason=reason, retryable=retryable) from exc

        image_bytes = _extract_inline_image(response)
        if image_bytes is None:
            raise ImageGenerationError(
                "Gemini returned no image (finish reason indicates a refusal or empty result).",
                reason="content_policy_refusal",
                retryable=False,
            )
        return image_bytes


def _classify_api_error(exc: APIError) -> tuple[str, bool]:
    code = getattr(exc, "code", None)
    if code == 429:
        return "rate_limited", True
    if code in (408, 504):
        return "timeout", True
    if code in (400, 403):
        return "content_policy_refusal", False
    return "unknown", False


def _extract_inline_image(response: "types.GenerateContentResponse") -> bytes | None:
    candidates = response.candidates or []
    if not candidates:
        return None
    candidate = candidates[0]
    finish_reason = str(getattr(candidate, "finish_reason", "") or "")
    if finish_reason.split(".")[-1] in _REFUSAL_FINISH_REASONS:
        return None

    content = candidate.content
    if content is None or not content.parts:
        return None
    for part in content.parts:
        inline_data = part.inline_data
        if inline_data is not None and inline_data.data:
            return inline_data.data
    return None


class OpenAIImageGenerationClient(ImageGenerationClient):
    """gpt-image-1 via OpenAI's `images.edit` endpoint -- an image-to-image
    edit call (source photo + text prompt), not `images.generate` (text-
    only, no source image input), since a before/after visualization has
    to actually start from the subject's own photo. gpt-image-1 always
    returns base64-encoded image bytes (no `url` response option, unlike
    dall-e-2/3), so this reads `b64_json` directly rather than needing to
    fetch a URL afterward."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise ImageGenerationError(
                "OPENAI_API_KEY is not configured -- add a real key to Backend/.env before "
                "triggering visual generation.",
                reason="unknown",
                retryable=False,
            )
        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key, timeout=settings.image_gen_request_timeout_seconds
        )
        self._model = settings.image_gen_model

    async def generate_before_after(self, *, source_image: bytes, prompt: str) -> bytes:
        try:
            response = await self._client.images.edit(
                model=self._model,
                image=("source.jpg", io.BytesIO(source_image), "image/jpeg"),
                prompt=prompt,
                # gpt-image-1-specific knobs (ignored/rejected by dall-e-2/3,
                # not that this codebase configures those): "high" input
                # fidelity keeps the edit closely anchored to the source
                # photo's identity/lighting/background, the same guarantee
                # IDENTITY_PRESERVATION_INSTRUCTION asks for in the prompt
                # itself -- belt and suspenders, not either/or.
                input_fidelity="high",
                quality="high",
                size="auto",
            )
        except OpenAIError as exc:
            reason, retryable = _classify_openai_error(exc)
            raise ImageGenerationError(str(exc), reason=reason, retryable=retryable) from exc

        if not response.data or not response.data[0].b64_json:
            raise ImageGenerationError(
                "OpenAI returned no image (content-policy refusal or empty result).",
                reason="content_policy_refusal",
                retryable=False,
            )
        return base64.b64decode(response.data[0].b64_json)


def _classify_openai_error(exc: OpenAIError) -> tuple[str, bool]:
    if isinstance(exc, RateLimitError):
        return "rate_limited", True
    if isinstance(exc, APITimeoutError):
        return "timeout", True
    if isinstance(exc, BadRequestError | PermissionDeniedError):
        return "content_policy_refusal", False
    return "unknown", False


@lru_cache
def get_image_generation_client() -> ImageGenerationClient:
    settings = get_settings()
    if settings.image_gen_provider == "gemini":
        return GeminiImageGenerationClient()
    if settings.image_gen_provider == "openai":
        return OpenAIImageGenerationClient()
    raise ValueError(f"Unsupported IMAGE_GEN_PROVIDER: {settings.image_gen_provider!r}")


async def generate_with_retry(
    client: ImageGenerationClient, *, source_image: bytes, prompt: str, max_retries: int
) -> bytes:
    """BR-006 cost control: only ImageGenerationError.retryable failures
    (timeout, rate-limited) are retried, with a short fixed backoff --
    never a content-policy refusal, which is a permanent outcome. Raises
    the last ImageGenerationError if all attempts are exhausted."""
    last_error: ImageGenerationError | None = None
    for attempt in range(max_retries + 1):
        try:
            return await client.generate_before_after(source_image=source_image, prompt=prompt)
        except ImageGenerationError as exc:
            last_error = exc
            if not exc.retryable or attempt >= max_retries:
                raise
            backoff = _RETRY_BACKOFF_SECONDS[min(attempt, len(_RETRY_BACKOFF_SECONDS) - 1)]
            await asyncio.sleep(backoff)
    assert last_error is not None  # loop always either returns or raises
    raise last_error
