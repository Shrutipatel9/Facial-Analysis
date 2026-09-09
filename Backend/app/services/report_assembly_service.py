"""Report assembly (FR-009-FR-012) -- pure functions, no DB/AI dependency,
independently unit-testable, same split as facial_measurement_service.py.

Wraps a completed FacialAnalysisResult's `measurements`/`narrative_result`
JSONB into the client-facing 11-section report shape. Deliberately makes
NO AI call: the report-level intro / "Understanding Your Results" /
limitations sections are static, branded template copy (FR-011's
"introduction", "preamble", "limitations/disclaimer" are structural,
standardized sections, not personalized narrative); only the closing
recommendations section reuses narrative_result.closing_recommendations,
already synthesized by Phase 4's own AI call. This keeps report generation
a fast, synchronous, cost-free data transform (BR-006 -- no new AI spend).

FR-012's three recommendation tiers (at-home/lifestyle, OTC/skincare-active,
in-clinic) are produced by a first-pass keyword heuristic over the existing
flat `recommendation_ideas` strings, not a dedicated AI call or a change to
Phase 4's already-implemented prompt -- delivery-team decision (ASM-007),
same "reasonable default, expect a tuning pass" posture as the photo-
validation thresholds (ASM-002) and the CV measurement formulas.

Payment now gates the START of analysis itself (analysis_service.
trigger_analysis, see D:\\zzz\\payment\\plans.md) -- a Report can only ever
be assembled from an already-paid, already-completed analysis. Even so,
`narrative_result` can still be `{}` here: the DeepSeek call can fail after
CV measurements already succeeded (the row stays "completed" regardless,
see analysis_service.run_analysis_pipeline's docstring), and a manual
pipeline retry is the practical fix. Each feature's `summary_callout` falls
back to a templated, non-AI string (_teaser_summary_callout) based purely
on measurement availability for exactly that gap, so a report is never
blank while a retry is pending. Once narrative_result is populated, the
real AI-authored summary_callout takes over automatically -- same field,
same shape, no API change.
"""

from typing import Any

from app.services.facial_measurement_service import ANALYSIS_FEATURES

_INTRO = (
    "This report is generated entirely by an automated, AI-based analysis of your submitted "
    "photos and questionnaire responses. It is not a medical diagnosis and has not been "
    "reviewed by a licensed professional. Findings are descriptive observations, not clinical "
    "conclusions. Where a finding suggests it may be worth discussing with a qualified "
    "professional, that is noted explicitly in context -- this report never replaces "
    "professional consultation."
)

_UNDERSTANDING_YOUR_RESULTS = (
    "This report is built from your uploaded photos and your answers to the onboarding "
    "questionnaire. Each of the following sections covers one facial feature area, always in "
    "the same structure: a short written analysis, what's already working well, and, where "
    "relevant, a suggestion worth considering. Where a recommendation is included, it is "
    "described in plain language rather than a numeric score, since this is an AI-generated "
    "assessment, not a diagnostic measurement."
)

_LIMITATIONS = (
    "This report is generated automatically and is informational only -- it is not a medical "
    "diagnosis, and it does not replace consultation with a qualified professional (such as a "
    "dermatologist or licensed aesthetics practitioner). Computer-vision measurements are "
    "approximate and derived from photo geometry, not clinical examination. Always consult a "
    "qualified professional before acting on any recommendation in this report."
)

# First-pass keyword buckets (ASM-007) -- not a clinical classifier. Order
# matters: a recommendation matching an in-clinic keyword is classified
# in-clinic even if it also happens to mention a product, since procedural
# language is the stronger signal of tier.
_IN_CLINIC_KEYWORDS = (
    "dermatologist",
    "consider seeing",
    "consult a",
    "professional treatment",
    "in-clinic",
    "in clinic",
    "laser",
    "filler",
    "botox",
    "peel",
    "microneedling",
    "surgical",
    "surgery",
    "injectable",
    "procedure",
)
_OTC_KEYWORDS = (
    "serum",
    "cream",
    "moisturizer",
    "cleanser",
    "spf",
    "sunscreen",
    "retinol",
    "vitamin c",
    "exfoliant",
    "toner",
    "product",
    "otc",
    "over-the-counter",
)


def _teaser_summary_callout(measurement: dict[str, Any]) -> str:
    """First-pass, non-AI fallback used only when no narrative exists yet
    (a post-payment AI failure) -- see module docstring."""
    if measurement.get("available"):
        return "Measurement captured."
    return "Assessed visually (no direct measurement)."


def _classify_one(text: str) -> str:
    lowered = text.lower()
    if any(keyword in lowered for keyword in _IN_CLINIC_KEYWORDS):
        return "in_clinic"
    if any(keyword in lowered for keyword in _OTC_KEYWORDS):
        return "otc_skincare"
    return "at_home"


def classify_recommendations(features: dict[str, dict[str, Any]], closing_recommendations: str) -> dict[str, list[str]]:
    """Buckets every feature's recommendation_ideas (plus the closing
    recommendations text, sentence-split) into the three FR-012 tiers.
    First-pass keyword heuristic -- see module docstring."""
    tiers: dict[str, list[str]] = {"at_home": [], "otc_skincare": [], "in_clinic": []}

    for feature_data in features.values():
        for idea in feature_data.get("recommendation_ideas", []) or []:
            tiers[_classify_one(idea)].append(idea)

    for sentence in closing_recommendations.split(". "):
        cleaned = sentence.strip().rstrip(".")
        if cleaned:
            tiers[_classify_one(cleaned)].append(cleaned if cleaned.endswith((".", "!", "?")) else f"{cleaned}.")

    return tiers


def assemble_sections(measurements: dict[str, Any], narrative_result: dict[str, Any]) -> dict[str, Any]:
    """Builds the full report `sections` JSON from a completed
    FacialAnalysisResult's two JSONB columns. Pure function, no I/O."""
    narrative_features = narrative_result.get("features", {})
    closing_recommendations = narrative_result.get("closing_recommendations", "")

    features: dict[str, Any] = {}
    for feature in ANALYSIS_FEATURES:
        narrative_entry = narrative_features.get(feature, {})
        measurement = measurements.get(feature) or {
            "available": False,
            "metrics": None,
            "note": "No measurement recorded.",
        }
        features[feature] = {
            "narrative": narrative_entry.get("narrative", ""),
            "summary_callout": narrative_entry.get("summary_callout") or _teaser_summary_callout(measurement),
            "strengths": narrative_entry.get("strengths", ""),
            "areas_of_note": narrative_entry.get("areas_of_note", ""),
            "projected_potential": narrative_entry.get("recommendation_ideas", []) or [],
            "measurement": measurement,
        }

    return {
        "intro": _INTRO,
        "understanding_your_results": _UNDERSTANDING_YOUR_RESULTS,
        "limitations": _LIMITATIONS,
        "features": features,
        "recommendations": classify_recommendations(narrative_features, closing_recommendations),
        "closing_recommendations": closing_recommendations,
    }
