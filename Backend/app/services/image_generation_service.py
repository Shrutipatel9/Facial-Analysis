"""AI image generation (FR-022, Milestone 2) -- turns a per-feature photo
crop plus a text prompt into an AI-generated "after" image for the report's
before/after visualization.

ASM-011: vendor is Google Gemini 2.5 Flash Image, user-confirmed
2026-09-11 (see docs/client_requirements.md). Unlike
app/services/ai_narrative_service.py's DeepSeek integration, this is NOT a
config-only swap -- DeepSeek happens to expose an OpenAI-Chat-Completions-
shaped API, so that module could just point the existing `openai` SDK at a
different base_url. Gemini's image-generation call shape (`contents=[...]`,
`response_modalities=["IMAGE"]`, inline-data image parts in the response)
has no such compatibility with anything already in this codebase, so there
is nothing to "point a base_url at" -- a real ImageGenerationClient ABC
exists here instead, mirroring PhotoStorage's precedent (a genuine
interface, not a config trick), so a future vendor swap has a real seam.

Cost control (BR-006): retries only cover transient failures (timeout,
rate-limited) with backoff, via generate_with_retry() below. A permanent
refusal (Gemini's safety/content-policy finish reasons) is never retried --
retrying a permanent refusal is exactly the kind of uncontrolled repeat
spend BR-006 warns about. Real Gemini calls never run in automated tests --
see tests/unit/test_image_generation_service.py, which mocks the
google.genai client boundary exclusively.
"""

import asyncio
from abc import ABC, abstractmethod
from functools import lru_cache

from google.genai import types
from google.genai.errors import APIError

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
        if not settings.image_gen_api_key:
            raise ImageGenerationError(
                "IMAGE_GEN_API_KEY is not configured -- add a real key to Backend/.env before "
                "triggering visual generation.",
                reason="unknown",
                retryable=False,
            )
        self._client = genai.Client(api_key=settings.image_gen_api_key)
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


@lru_cache
def get_image_generation_client() -> ImageGenerationClient:
    settings = get_settings()
    if settings.image_gen_provider == "gemini":
        return GeminiImageGenerationClient()
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
