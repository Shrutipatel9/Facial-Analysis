"""AI narrative generation (FR-008) -- turns CV measurements + questionnaire
answers + the actual photos into a structured, per-feature narrative draft
that report-generation (Phase 5) later wraps into the client-facing report.

NFR-008 (client-stated) names OpenAI; this ran against DeepSeek instead for
a while (delivery-team decision, ASM-006 -- client_requirements.md v1.8,
flagged for client awareness, not silent), since DeepSeek's hosted API is
OpenAI-Chat-Completions-compatible -- this uses the `openai` SDK pointed at
a configurable base_url, so the v1.27 switch back to real OpenAI was a
config change (AI_BASE_URL/OPENAI_API_KEY/AI_MODEL), not a new
implementation. No ABC/interface layer here (unlike EmailSender/
PhotoStorage) -- DeepSeek and OpenAI are API-shape-compatible, so a full
interface would be premature abstraction for what is actually just a
configuration swap.

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


# Per-feature named sub-section headings -- 2026-09-17, user-directed: a
# full re-check of the client's reference PDF found every feature page is
# actually broken into multiple separately-headed narrative sub-sections
# (e.g. Hair: "Hair Style" / "Hair Loss" / "Hair Health"; Eyebrows+Eyes:
# "Eyebrows" / "Eyelashes" / "Eyes" / "Under eye"), not the single
# `narrative` paragraph this project generated until now -- replaces that
# field with a `sections` object keyed by exactly these headings, same
# "sanitize against a fixed vocabulary" pattern as _FEATURE_ATTRIBUTE_KEYS
# above (see _sanitize_sections). Single-section features keep the same
# heading report_pdf_service.py's retired _PRIMARY_SUBHEADING dict already
# used, so only Hair/Eyebrows/Eyes/Neck actually gain new distinct
# sub-sections; the others just get a longer, deeper version of what they
# already had under the same heading.
_FEATURE_SUBSECTIONS: dict[str, tuple[str, ...]] = {
    "hair": ("Hair Style", "Hair Loss", "Hair Health"),
    "eyebrows": ("Eyebrows", "Eyelashes"),
    "eyes": ("Eyes", "Under Eye"),
    "nose": ("Nose",),
    "cheeks": ("Cheek Structure",),
    "jaw": ("Jaw Structure",),
    "lips": ("Lips",),
    "chin": ("Chin",),
    "skin": ("Skincare Protocol",),
    "neck": ("Neck Size", "Neck Skin"),
    "ears": ("Ear Structure",),
}


def _subsection_vocabulary_prompt() -> str:
    lines = [f"- {feature}: {', '.join(headings)}" for feature, headings in _FEATURE_SUBSECTIONS.items()]
    return "\n".join(lines)


_SYSTEM_PROMPT = (
    "You are a facial-analysis assistant for a non-surgical aesthetics platform. "
    "You are given CV-derived facial measurements, a user's onboarding questionnaire "
    "answers (each paired with its actual question text), and photos of their face "
    "from three angles. Write a narrative analysis covering exactly these 11 "
    "features, in this order: "
    f"{', '.join(ANALYSIS_FEATURES)}. "
    "For each feature, first classify it into the named attributes listed below for that "
    'feature -- short plain-language values (e.g. "Wide", "Soft arch", "Moderate"), '
    "assessed directly from the photos. Omit a key entirely (do not include it in the "
    "attributes object) whenever it genuinely isn't assessable from the photos (covered, "
    "cropped out of frame, unclear angle) -- never guess a value just to fill every key. "
    "Attribute vocabulary per feature (classify only these keys, per feature):\n"
    f"{_attribute_vocabulary_prompt()}\n"
    "Second, write one detailed narrative sub-section per named heading listed below for "
    "that feature -- most features have one heading, some have two or three; write a "
    "separate, substantial entry for each one, never combining multiple headings into a "
    "single entry or leaving one out. Sub-section headings per feature (write exactly these "
    "headings, per feature, nothing else):\n"
    f"{_subsection_vocabulary_prompt()}\n"
    "Each sub-section's content must be 8-12 sentences of specific, informational "
    "observations grounded in the actual measurements, photos, and your own attribute "
    "classifications above -- never generic filler, and never a short summary; this is the "
    "detailed body of the report, matching the depth and thoroughness of a real "
    "clinical-style write-up a person would pay for, not a quick overview. Cover multiple "
    "distinct angles within the sub-section rather than restating one observation in "
    "different words: what the measurements/attributes show, how that compares to typical "
    "proportions or presentations for this feature, what it contributes to overall facial "
    "harmony/balance, and any nuance worth calling out (asymmetry, a borderline "
    "classification, something the photos show that the attribute vocabulary alone doesn't "
    "capture). Longer and more thorough is always preferable to shorter here -- there is no "
    "length penalty, so use the full range and favor the higher end (10-12 sentences) "
    "whenever the feature has enough real signal (measurements, clear attributes, or "
    "clearly visible detail in the photos) to support it; only stay closer to the lower end "
    "when a feature genuinely has little to observe. "
    "Naturally weave at least 3-4 of that feature's classified attribute values into each "
    "sub-section's sentences (e.g. \"a soft arch brow in a mid-set position with thick "
    "density\"), the same way you'd cite a measurement -- write it as natural prose, never "
    "as a raw 'key: value' pair or the literal attribute key name; when a feature has "
    "multiple sub-sections, don't just repeat the same attributes in each one -- draw out "
    "what's specifically relevant to that sub-section's own topic (e.g. Hair's \"Hair Loss\" "
    'sub-section should focus on hairline/density/thinning-relevant attributes, while "Hair '
    "Style\" focuses on texture/parting/styling-relevant ones). When a feature's measurement "
    "data shows it is available, naturally cite the actual metric value in multiple "
    'sentences across that feature\'s sub-sections, not just once (e.g. "your eye width '
    'ratio of 0.42..." in one sentence, and a second, different metric cited later in the '
    'same or another sub-section) -- not just a vague reference to "the measurements" -- '
    "when no measurement is available "
    "for a feature, ground every sub-section in the photos and your attribute "
    "classifications instead, in the same descriptive depth. "
    "Use the questionnaire context to personalize tone, not to invent facts: "
    'reference the user\'s stated goal ("What is your goal?") when framing ambition '
    "in the closing recommendations, and their stated motivation for signing up so "
    "the closing paragraph reads as synthesis of this specific user, not boilerplate. "
    "When discussing a feature the user explicitly named as something they like most "
    "or dislike most about their face, acknowledge that naturally and empathetically -- "
    "still strictly observational, never framed as something to 'fix'. If the "
    "questionnaire indicates elevated distress about their appearance or frequent "
    "preoccupation with it, use an especially measured, reassuring tone throughout and "
    "reinforce more explicitly than usual that this report is informational only, not "
    "a judgment. Never reference the user's answers about medical conditions, "
    "medications, or allergies anywhere in any sub-section -- those exist for internal "
    "context only, never for cosmetic commentary. "
    "Tone is strictly informational, never diagnostic or prescriptive: never claim a "
    "medical diagnosis, never say a treatment is required, and always frame any "
    "recommendation as something to discuss with a qualified professional, not an "
    "instruction. Do not reference Body Dysmorphic Disorder or make judgments about "
    "the user's appearance being flawed -- describe features neutrally. Any cost "
    "estimate given anywhere in this response is illustrative only, never a "
    "guaranteed price -- always approximate, and actual pricing should be confirmed "
    "with a professional or retailer. "
    "Respond with a single JSON object with exactly four top-level keys: "
    '"features" (an object keyed by each of the 11 feature names, each value an object with: '
    '"attributes" -- an object with only the keys from that feature\'s vocabulary above that '
    "you could actually classify, each a short plain-language value string (never the raw key "
    "name as the value, never a key not in that feature's own vocabulary list, never every key "
    "forced-filled); "
    '"sections" -- an object keyed by exactly that feature\'s own sub-section headings from '
    "the list above (all of them, never a subset, never a heading outside that feature's own "
    "list), each value an 8-12 sentence sub-section body as described above; "
    '"summary_callout" -- one full sentence summarizing this feature "at a glance", suitable for '
    "a report overview table; "
    '"strengths" -- two to three sentences naming what is already working well for this '
    "feature, evidence-grounded (cite an attribute or measurement where relevant), never "
    "fabricated praise -- one sentence is too thin here, give real substance; "
    '"areas_of_note" -- two to three sentences naming what is worth being aware of for this '
    'feature, in the same evidence-grounded depth, or "None notable." if genuinely nothing '
    "stands out -- never invented just to fill the field; "
    'and "recommendation_ideas" (an array of 1-3 objects, each describing one concrete '
    'suggestion, with exactly these keys: "text" (a complete suggestion sentence, same '
    'style as before); "cost" (a short, approximate USD estimate or range for that '
    'specific suggestion, e.g. "$15-25" for a product or "$200-400" for an in-clinic '
    "procedure, phrased always as an estimate, never a guaranteed price, since actual "
    "pricing varies by provider, region, and brand -- use JSON null if the suggestion has "
    'no meaningful cost, e.g. a lifestyle habit like "get more sleep"); "cadence" (a short '
    'frequency/schedule phrase, e.g. "Nightly", "Daily, 5 min AM", "Weekly", "Monthly", '
    '"One-time", or JSON null if a schedule genuinely doesn\'t apply); "time_to_effect" (a '
    "short phrase for how long until a visible effect is plausible, e.g. \"Immediate\", "
    '"2-4 weeks", "8+ weeks", or JSON null if not knowable); and "difficulty" (exactly one '
    'of "Easy", "Medium", or "Hard" describing how much daily effort or commitment the '
    "suggestion takes, or JSON null if it doesn't apply); \"category\" (exactly one of "
    '"Cosmetic", "Lifestyle", or "Clinical" describing what kind of change the suggestion '
    'is, or JSON null if it genuinely doesn\'t fit one of those); "risk_level" (exactly one '
    'of "Low", "Medium", or "High" describing the suggestion\'s safety/reversibility risk, '
    'or JSON null if not applicable); "product_or_method" (a short name of the specific '
    'product or method the suggestion refers to, e.g. "Eyebrow Tinting Kit" or "0.5% Retinol '
    'Serum", or JSON null if the suggestion is a general habit with no specific product or '
    'method); and "tier" (exactly one of "at_home", "otc_skincare", or "in_clinic" '
    "classifying where this suggestion belongs: \"at_home\" for a free lifestyle/habit change "
    "with no product or professional involved, \"otc_skincare\" for an over-the-counter "
    'product a person buys and uses themselves, "in_clinic" for anything requiring a '
    "professional/procedure/prescription -- or JSON null if the suggestion genuinely doesn't "
    "fit one of those three -- use JSON null for any of these eight fields rather than "
    "guessing a value you aren't confident about, same posture as every other optional field "
    "in this prompt)), "
    '"closing_recommendations" (a synthesis across all 11 features, personalized per the goal/'
    "motivation guidance above, written as exactly 4 substantial, thorough paragraphs (5-8 "
    "sentences each, not short) separated by a blank line (\\n\\n) in this fixed order: (1) "
    "overall facial harmony and the primary structural/skeletal priorities, (2) the "
    "periorbital/eye region and its priorities, (3) hair and lower-face grooming "
    "priorities, (4) a practical, sequenced next-steps paragraph -- every point made "
    "across these 4 paragraphs must trace back to a finding already covered in the per-feature "
    "sections above, never a new finding introduced here for the first time), "
    '"facial_age" (your best estimate of the subject\'s apparent age from the photos alone, as '
    'an object {"estimate": <integer years>, "note": <one short sentence of context>} -- this is '
    "an apparent-age visual estimate, not a medical or biological age claim; if the photos "
    "genuinely don't give you enough to estimate confidently, use JSON null instead of guessing), "
    'and "hair_loss" (an object {"stage": <integer 1-7>, "label": <short plain-language stage '
    "name>} placing the subject on a 7-point scale from 1=no visible thinning/recession to "
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
    if not settings.openai_api_key:
        raise AIProviderError(
            "OPENAI_API_KEY is not configured -- add a real key to Backend/.env before triggering analysis."
        )
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
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


def _sanitize_sections(feature: str, raw: Any) -> dict[str, str]:
    """Same sanitize-against-a-fixed-vocabulary posture as
    _sanitize_attributes, for the per-feature narrative sub-sections
    (_FEATURE_SUBSECTIONS) -- drops any hallucinated heading not in that
    feature's own list and any non-string/empty value. Unlike
    _sanitize_attributes, iterates the vocabulary (not `raw`) so the
    result always comes back in the fixed canonical heading order
    regardless of what order the model emitted them in -- report_pdf_
    service.py and FeatureSection.tsx both render sections in whatever
    order this dict returns, with no re-sorting of their own."""
    if not isinstance(raw, dict):
        return {}
    allowed = _FEATURE_SUBSECTIONS.get(feature, ())
    return {heading: raw[heading] for heading in allowed if isinstance(raw.get(heading), str) and raw[heading]}


_ALLOWED_RECOMMENDATION_DIFFICULTIES = ("Easy", "Medium", "Hard")
# FR-024 (Milestone 3) -- same closed-vocabulary posture as difficulty:
# each drives a colored badge/tag on the frontend, so an unrecognized
# value is dropped to None rather than passed through as free text.
_ALLOWED_RECOMMENDATION_CATEGORIES = ("Cosmetic", "Lifestyle", "Clinical")
_ALLOWED_RECOMMENDATION_RISK_LEVELS = ("Low", "Medium", "High")
# FR-029 (Milestone 4) -- same closed-vocabulary posture: drives
# report_assembly_service.classify_recommendations' tier bucketing
# directly when present, only falling back to its keyword heuristic when
# this is None (either the model returned null, or -- for every report
# persisted before this field existed -- the key is simply absent).
_ALLOWED_RECOMMENDATION_TIERS = ("at_home", "otc_skincare", "in_clinic")


def _sanitize_recommendation_ideas(raw: Any) -> list[dict[str, Any]]:
    """FR-025/FR-024 -- same 'never fail the whole feature over one bad
    item' posture as _sanitize_attributes/_sanitize_sections. Tolerates a
    bare string item (in case the model ignores the structured-object
    instruction for one entry) by treating it as {"text": item} with every
    metadata field absent, rather than dropping the whole recommendation
    over a formatting slip. Drops items with no usable text entirely, and
    drops any difficulty/category/risk_level value outside its fixed
    vocabulary to None rather than passing an unrecognized value through
    as free text -- each drives a colored badge downstream, so none of
    them can be an unbounded string."""
    if not isinstance(raw, list):
        return []

    def _clean_str(item: dict[str, Any], key: str) -> str | None:
        value = item.get(key)
        return value if isinstance(value, str) and value else None

    sanitized: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, str) and item:
            sanitized.append(
                {
                    "text": item,
                    "cost": None,
                    "cadence": None,
                    "time_to_effect": None,
                    "difficulty": None,
                    "category": None,
                    "risk_level": None,
                    "product_or_method": None,
                    "tier": None,
                }
            )
            continue
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if not isinstance(text, str) or not text:
            continue
        difficulty = item.get("difficulty")
        category = item.get("category")
        risk_level = item.get("risk_level")
        tier = item.get("tier")
        sanitized.append(
            {
                "text": text,
                "cost": _clean_str(item, "cost"),
                "cadence": _clean_str(item, "cadence"),
                "time_to_effect": _clean_str(item, "time_to_effect"),
                "difficulty": difficulty if difficulty in _ALLOWED_RECOMMENDATION_DIFFICULTIES else None,
                "category": category if category in _ALLOWED_RECOMMENDATION_CATEGORIES else None,
                "risk_level": risk_level if risk_level in _ALLOWED_RECOMMENDATION_RISK_LEVELS else None,
                "product_or_method": _clean_str(item, "product_or_method"),
                "tier": tier if tier in _ALLOWED_RECOMMENDATION_TIERS else None,
            }
        )
    return sanitized


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
            entry["sections"] = _sanitize_sections(feature, entry.get("sections"))
            entry["recommendation_ideas"] = _sanitize_recommendation_ideas(entry.get("recommendation_ideas"))

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
            # 2026-09-18: per-feature `sections` content is now up to 16
            # separately-headed 8-12 sentence sub-sections across the 11
            # features, plus longer strengths/areas_of_note and a 4-paragraph
            # closing_recommendations (5-8 sentences each) -- pushes
            # estimated total output well past the prior 8192 budget.
            # gpt-4o's real completion-token ceiling is 16384; set just under
            # that so a genuinely long response still has headroom rather
            # than being silently truncated (which would fail JSON parsing
            # in _parse_response).
            max_tokens=8192,
        )
    except OpenAIError as exc:
        raise AIProviderError(f"AI provider request failed: {exc}") from exc

    raw_content = response.choices[0].message.content if response.choices else None
    if not raw_content:
        raise AIProviderError("AI provider returned an empty response.")

    return _parse_response(raw_content)
