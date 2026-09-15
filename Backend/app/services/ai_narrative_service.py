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

# Per-feature named-attribute vocabulary -- the client's own reference
# report (MyFace-Protocol-test-1.pdf) turns out to be driven by a rich
# per-feature classification layer (e.g. Hair: hairline/forehead exposure/
# texture/parting/crown coverage/density/color), not freeform prose over
# raw ratios -- that classification depth, not model choice, is what this
# key adds. The AI classifies each feature into these named attributes
# (short plain-language values, e.g. "Wide", "Soft arch", "Moderate") from
# the photos, in the same existing multimodal call -- no new AI request.
# A key is omitted entirely (never guessed) when genuinely not assessable
# from the photos, same "say less" posture as facial_age/hair_loss.
# Eyelash and under-eye attributes fold into "eyes" rather than becoming
# new top-level features, same precedent as Smile folding into Lips
# (BR-011) -- the fixed 11-feature set (BR-008) is unchanged.
_FEATURE_ATTRIBUTE_KEYS: dict[str, tuple[str, ...]] = {
    "hair": ("hairline", "forehead_exposure", "texture", "parting", "crown_coverage", "density", "hair_color"),
    "eyebrows": ("arch", "position", "density", "apex"),
    "eyes": (
        "canthal_tilt",
        "eyelid_exposure",
        "lower_lid_curvature",
        "lash_density",
        "under_eye_pigmentation",
        "under_eye_hollowing",
    ),
    "nose": ("dorsal_contour", "alar_base_width", "nasolabial_angle", "frontal_proportions"),
    "cheeks": ("cheekbone_height", "cheekbone_projection", "cheek_width", "jaw_to_cheek_transition", "symmetry"),
    "jaw": ("mandibular_definition", "transverse_width", "gonial_angle", "contour_smoothness"),
    "lips": ("vermilion_volume", "philtrum_length", "cupids_bow_definition"),
    "chin": ("shape", "height", "width", "projection", "labiomental_angle"),
    "skin": ("texture", "tone_evenness", "redness", "under_eye_shadowing"),
    "neck": ("width", "length", "jaw_neck_transition", "head_posture"),
    "ears": ("symmetry", "prominence", "position"),
}

def _attribute_vocabulary_prompt() -> str:
    lines = [f"- {feature}: {', '.join(keys)}" for feature, keys in _FEATURE_ATTRIBUTE_KEYS.items()]
    return "\n".join(lines)


_SYSTEM_PROMPT = (
    "You are a facial-analysis assistant for a non-surgical aesthetics platform. "
    "You are given CV-derived facial measurements, a user's onboarding questionnaire "
    "answers (each paired with its actual question text), and photos of their face "
    "from three angles. Write a narrative analysis covering exactly these 11 "
    "features, in this order: "
    f"{', '.join(ANALYSIS_FEATURES)}. "
    "For each feature, first classify it into the named attributes listed below for that "
    "feature -- short plain-language values (e.g. \"Wide\", \"Soft arch\", \"Moderate\"), "
    "assessed directly from the photos. Omit a key entirely (do not include it in the "
    "attributes object) whenever it genuinely isn't assessable from the photos (covered, "
    "cropped out of frame, unclear angle) -- never guess a value just to fill every key. "
    "Attribute vocabulary per feature (classify only these keys, per feature):\n"
    f"{_attribute_vocabulary_prompt()}\n"
    "For each feature, write specific, informational observations grounded in "
    "the actual measurements, photos, and your own attribute classifications above -- "
    "never generic filler. Naturally weave at least 2-3 of that feature's classified "
    "attribute values into the narrative sentences themselves (e.g. \"a soft arch "
    "brow in a mid-set position with thick density\"), the same way you'd cite a "
    "measurement -- write it as natural prose, never as a raw 'key: value' pair or "
    "the literal attribute key name. When a "
    "feature's measurement data shows it is available, naturally cite the actual "
    "metric value in at least one sentence of the narrative (e.g. \"your eye width "
    "ratio of 0.42...\"), not just a vague reference to \"the measurements\" -- when "
    "no measurement is available for a feature, ground the narrative in the photos "
    "and your attribute classifications instead. "
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
    "Respond with a single JSON object with exactly four top-level keys: "
    '"features" (an object keyed by each of the 11 feature names, each value an object with: '
    '"attributes" -- an object with only the keys from that feature\'s vocabulary above that '
    "you could actually classify, each a short plain-language value string (never the raw key "
    "name as the value, never a key not in that feature's own vocabulary list, never every key "
    "forced-filled); "
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
    'sentence)), '
    '"closing_recommendations" (a synthesis across all 11 features, personalized per the goal/'
    "motivation guidance above, written as exactly 4 short paragraphs separated by a blank line "
    "(\\n\\n) in this fixed order: (1) overall facial harmony and the primary structural/skeletal "
    "priorities, (2) the periorbital/eye region and its priorities, (3) hair and lower-face "
    "grooming priorities, (4) a practical, sequenced next-steps paragraph -- every point made "
    "across these 4 paragraphs must trace back to a finding already covered in the per-feature "
    "narratives above, never a new finding introduced here for the first time), "
    '"facial_age" (your best estimate of the subject\'s apparent age from the photos alone, as '
    'an object {"estimate": <integer years>, "note": <one short sentence of context>} -- this is '
    "an apparent-age visual estimate, not a medical or biological age claim; if the photos "
    "genuinely don't give you enough to estimate confidently, use JSON null instead of guessing), "
    'and "hair_loss" (an object {"stage": <integer 1-7>, "label": <short plain-language stage '
    'name>} placing the subject on a 7-point scale from 1=no visible thinning/recession to '
    "7=extensive/advanced hair loss, based only on what's visible in the photos -- use JSON null "
    "if hair is not clearly visible enough to assess, e.g. covered, cropped out of frame, or a "
    "camera angle that doesn't show the hairline)."
)


@dataclass(frozen=True)
class NarrativeResult:
    features: dict[str, dict[str, Any]]
    closing_recommendations: str
    # report_design_spec.md v3.0 §15/§13.3 -- both None whenever the model
    # didn't return a confident estimate (see _parse_response); never
    # defaulted to a fabricated value here or downstream.
    facial_age: dict[str, Any] | None = None
    hair_loss: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "features": self.features,
            "closing_recommendations": self.closing_recommendations,
            "facial_age": self.facial_age,
            "hair_loss": self.hair_loss,
        }


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


def format_questionnaire_context(answers: dict[str, Any]) -> str:
    """Pairs each answered question with its actual question text (from
    questionnaire_service.QUESTIONS_BY_ID) instead of a raw {"q4": "..."}
    JSON dump -- the AI otherwise has no way to know what an opaque
    question id like "q15" actually asked. Unanswered/hidden questions are
    naturally absent from `answers` (see questionnaire_service.is_visible)
    and simply don't produce a line; an unrecognized key (shouldn't happen
    in practice) is skipped rather than raising, since this is best-effort
    context, not validation.

    Public (not module-private) since chat_service.py (Milestone 2 Phase
    12) reuses it for the same "give the AI real question text, not opaque
    ids" need -- same posture as image_generation_service.py's
    IDENTITY_PRESERVATION_INSTRUCTION being promoted for a second caller.
    """
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
    questionnaire_context = format_questionnaire_context(questionnaire_answers)
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


def _parse_facial_age(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    estimate = raw.get("estimate")
    if not isinstance(estimate, int) or isinstance(estimate, bool) or not (0 < estimate < 120):
        return None
    note = raw.get("note")
    return {"estimate": estimate, "note": note if isinstance(note, str) else None}


def _parse_hair_loss(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    stage = raw.get("stage")
    label = raw.get("label")
    if not isinstance(stage, int) or isinstance(stage, bool) or not (1 <= stage <= 7):
        return None
    if not isinstance(label, str) or not label:
        return None
    return {"stage": stage, "label": label}


def _sanitize_attributes(feature: str, raw: Any) -> dict[str, str]:
    """Keeps only the keys in that feature's own vocabulary
    (_FEATURE_ATTRIBUTE_KEYS) with a non-empty string value -- drops any
    hallucinated key not in the vocabulary and any non-string value,
    rather than failing the whole feature over one bad attribute."""
    if not isinstance(raw, dict):
        return {}
    allowed = _FEATURE_ATTRIBUTE_KEYS.get(feature, ())
    return {key: value for key, value in raw.items() if key in allowed and isinstance(value, str) and value}


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

    for feature in ANALYSIS_FEATURES:
        entry = features[feature]
        if isinstance(entry, dict):
            entry["attributes"] = _sanitize_attributes(feature, entry.get("attributes"))

    # facial_age/hair_loss are best-effort estimates layered onto the same
    # call -- a missing, null, or malformed value here means "the model
    # couldn't confidently estimate this", not a reason to fail the whole
    # narrative (report_template.md §13: if evidence is missing, say less).
    return NarrativeResult(
        features=features,
        closing_recommendations=closing,
        facial_age=_parse_facial_age(parsed.get("facial_age")),
        hair_loss=_parse_hair_loss(parsed.get("hair_loss")),
    )


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
