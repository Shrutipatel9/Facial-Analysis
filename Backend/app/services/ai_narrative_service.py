"""AI narrative generation (FR-008) -- turns CV measurements + questionnaire
answers + the actual photos into a structured, per-feature narrative draft
that report-generation (Phase 5) later wraps into the client-facing report.

NFR-008 (client-stated) names OpenAI; this is built against DeepSeek
instead (delivery-team decision, ASM-006 -- client_requirements.md v1.8,
flagged for client awareness, not silent). DeepSeek's hosted API is
OpenAI-Chat-Completions-compatible, so this uses the `openai` SDK pointed
at a configurable base_url -- switching to real OpenAI later is a config
change (AI_BASE_URL/AI_API_KEY/AI_MODEL), not a new implementation. No
ABC/interface layer here (unlike EmailSender/PhotoStorage) -- DeepSeek and
OpenAI are API-shape-compatible, so a full interface would be premature
abstraction for what is actually just a configuration swap.

Multimodal: the actual photos are sent as base64 images alongside the
measurements and questionnaire text (FR-008's "not photo analysis alone",
NFR-008's literal "Vision" naming) -- see docs/security.md §7, photo bytes
now leave the system to the configured AI provider.
"""

import base64
import io
import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from openai import AsyncOpenAI, OpenAIError
from PIL import Image

from app.core.config import get_settings
from app.exceptions import AIProviderError
from app.services.facial_measurement_service import ANALYSIS_FEATURES, MeasurementResult
from app.services.questionnaire_service import QUESTIONS_BY_ID

_MAX_IMAGE_DIMENSION = 1024
_JPEG_QUALITY = 85

_SYSTEM_PROMPT = (
    "You are a facial-analysis assistant for a non-surgical aesthetics platform. "
    "You are given CV-derived facial measurements, a user's onboarding questionnaire "
    "answers (each paired with its actual question text), and photos of their face "
    "from three angles. Write a narrative analysis covering exactly these 11 "
    "features, in this order: "
    f"{', '.join(ANALYSIS_FEATURES)}. "
    "For each feature, write specific, informational observations grounded in "
    "the actual measurements and photos provided -- never generic filler. When a "
    "feature's measurement data shows it is available, naturally cite the actual "
    "metric value in at least one sentence of the narrative (e.g. \"your eye width "
    "ratio of 0.42...\"), not just a vague reference to \"the measurements\" -- when "
    "no measurement is available for a feature, ground the narrative in the photos "
    "alone instead. "
    "Use the questionnaire context to personalize tone, not to invent facts: "
    "reference the user's stated goal (\"What is your goal?\") when framing ambition "
    "in the closing recommendations, and their stated motivation for signing up so "
    "the closing paragraph reads as synthesis of this specific user, not boilerplate. "
    "When discussing a feature the user explicitly named as something they like most "
    "or dislike most about their face, acknowledge that naturally and empathetically -- "
    "still strictly observational, never framed as something to 'fix'. If the "
    "questionnaire indicates elevated distress about their appearance or frequent "
    "preoccupation with it, use an especially measured, reassuring tone throughout and "
    "reinforce more explicitly than usual that this report is informational only, not "
    "a judgment. Never reference the user's answers about medical conditions, "
    "medications, or allergies anywhere in the narrative -- those exist for internal "
    "context only, never for cosmetic commentary. "
    "Tone is strictly informational, never diagnostic or prescriptive: never claim a "
    "medical diagnosis, never say a treatment is required, and always frame any "
    "recommendation as something to discuss with a qualified professional, not an "
    "instruction. Do not reference Body Dysmorphic Disorder or make judgments about "
    "the user's appearance being flawed -- describe features neutrally. "
    "Respond with a single JSON object with exactly two top-level keys: "
    '"features" (an object keyed by each of the 11 feature names, each value an object with: '
    '"narrative" -- 3-5 sentences of detailed, specific observations, grounded in the '
    "measurements/photos as described above; "
    '"summary_callout" -- one full sentence summarizing this feature "at a glance", suitable for '
    'a report overview table; '
    '"strengths" -- one short sentence naming something that is already working well for this '
    'feature, evidence-grounded, never fabricated praise; '
    '"areas_of_note" -- one short sentence naming something worth being aware of for this '
    'feature, or "None notable." if genuinely nothing stands out -- never invented just to fill '
    'the field; '
    'and "recommendation_ideas" (an array of 1-3 short strings, each a complete suggestion '
    'sentence)), and '
    '"closing_recommendations" (a short paragraph synthesizing all 11 features, personalized '
    "per the goal/motivation guidance above)."
)


@dataclass(frozen=True)
class NarrativeResult:
    features: dict[str, dict[str, Any]]
    closing_recommendations: str

    def to_dict(self) -> dict[str, Any]:
        return {"features": self.features, "closing_recommendations": self.closing_recommendations}


@lru_cache
def get_ai_client() -> AsyncOpenAI:
    settings = get_settings()
    if not settings.ai_api_key:
        raise AIProviderError(
            "AI_API_KEY is not configured -- add a real key to Backend/.env before "
            "triggering analysis."
        )
    return AsyncOpenAI(
        api_key=settings.ai_api_key,
        base_url=settings.ai_base_url,
        timeout=settings.ai_request_timeout_seconds,
    )


def _to_jpeg_data_url(content: bytes) -> str:
    image = Image.open(io.BytesIO(content)).convert("RGB")
    if max(image.size) > _MAX_IMAGE_DIMENSION:
        image.thumbnail((_MAX_IMAGE_DIMENSION, _MAX_IMAGE_DIMENSION))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=_JPEG_QUALITY)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _format_questionnaire_context(answers: dict[str, Any]) -> str:
    """Pairs each answered question with its actual question text (from
    questionnaire_service.QUESTIONS_BY_ID) instead of a raw {"q4": "..."}
    JSON dump -- the AI otherwise has no way to know what an opaque
    question id like "q15" actually asked. Unanswered/hidden questions are
    naturally absent from `answers` (see questionnaire_service.is_visible)
    and simply don't produce a line; an unrecognized key (shouldn't happen
    in practice) is skipped rather than raising, since this is best-effort
    context, not validation."""
    lines: list[str] = []
    for question_id, answer in answers.items():
        question = QUESTIONS_BY_ID.get(question_id)
        if question is None or answer in (None, ""):
            continue
        lines.append(f"{question.text}: {answer}")
    return "\n".join(lines)


def _build_user_content(
    measurements: dict[str, MeasurementResult], questionnaire_answers: dict[str, Any], photos: dict[str, bytes]
) -> list[dict[str, Any]]:
    measurements_json = json.dumps({key: value.to_dict() for key, value in measurements.items()})
    questionnaire_context = _format_questionnaire_context(questionnaire_answers)
    content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                f"CV measurements (JSON): {measurements_json}\n\n"
                f"Questionnaire answers (question: answer, one per line):\n{questionnaire_context}"
            ),
        }
    ]
    for angle in ("front", "left_3q", "right_3q"):
        photo_bytes = photos.get(angle)
        if photo_bytes is not None:
            content.append({"type": "image_url", "image_url": {"url": _to_jpeg_data_url(photo_bytes)}})
    return content


def _parse_response(raw_content: str) -> NarrativeResult:
    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        raise AIProviderError("AI response was not valid JSON.") from exc

    features = parsed.get("features")
    closing = parsed.get("closing_recommendations")
    if not isinstance(features, dict) or not isinstance(closing, str):
        raise AIProviderError("AI response was missing expected 'features'/'closing_recommendations' keys.")

    missing = [feature for feature in ANALYSIS_FEATURES if feature not in features]
    if missing:
        raise AIProviderError(f"AI response is missing features: {', '.join(missing)}.")

    return NarrativeResult(features=features, closing_recommendations=closing)


async def generate_narrative(
    measurements: dict[str, MeasurementResult],
    questionnaire_answers: dict[str, Any],
    photos: dict[str, bytes],
) -> NarrativeResult:
    settings = get_settings()
    client = get_ai_client()
    user_content = _build_user_content(measurements, questionnaire_answers, photos)

    try:
        response = await client.chat.completions.create(  # type: ignore[call-overload]
            model=settings.ai_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
        )
    except OpenAIError as exc:
        raise AIProviderError(f"AI provider request failed: {exc}") from exc

    raw_content = response.choices[0].message.content if response.choices else None
    if not raw_content:
        raise AIProviderError("AI provider returned an empty response.")

    return _parse_response(raw_content)
