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

Milestone 2 (FR-018) addition: `facial_assessments` is an optional third
argument (default None, backward-compatible with any existing caller/test
that only passes the original two) carrying the already-computed
dimorphism/prototypicality/proportions/symmetry/face_shape blob from
FacialAnalysisResult.facial_assessments -- itself nullable, so a report
assembled from a pre-Milestone-2 analysis row still gets a fully-shaped,
all-`available:false` `facial_assessments` section here rather than a
missing key. `feature_scores`/`overall_score`/`harmony_chart` are derived
here, on every assembly, from `measurements`+`facial_assessments` --
cheap and pure, so there is no reason to persist them as a third JSONB
column when assembly already recomputes everything else on read.
"""

from typing import Any

from app.services.facial_assessment_service import (
    ASSESSMENT_CATEGORIES,
    AssessmentResult,
    compute_feature_scores,
    compute_harmony_chart,
    compute_overall_score,
)
from app.services.facial_measurement_service import ANALYSIS_FEATURES, MeasurementResult

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


def recommendation_text(idea: Any) -> str:
    """FR-025 (Milestone 3) -- extracts display text from one recommendation
    idea, tolerating both the pre-Milestone-3 bare-string shape and the
    Milestone-3 structured-object shape (an already-persisted
    FacialAnalysisResult.narrative_result row can be either, forever -- no
    backfill migration touches existing data). Public (no leading
    underscore): report_visual_service.py, ai_visual_service.py, and
    report_pdf_service.py all read recommendation_ideas/projected_potential
    directly and need this same extraction, rather than each growing its
    own private copy."""
    if isinstance(idea, dict):
        text = idea.get("text")
        return text if isinstance(text, str) else ""
    return idea if isinstance(idea, str) else ""


def normalize_recommendation_item(idea: Any) -> dict[str, Any] | None:
    """FR-025/FR-024 -- coerces one recommendation idea (either shape
    above) into the structured object shape RecommendationItemOut
    (app/schemas/reports.py) requires. Returns None for an item with no
    usable text at all (defensive -- should not happen for either on-disk
    shape). category/risk_level/product_or_method (FR-024) default to None
    the same way as every other optional field here -- a pre-Phase-15
    persisted item simply has no such keys, .get() naturally yields None."""
    text = recommendation_text(idea)
    if not text:
        return None
    is_dict = isinstance(idea, dict)
    difficulty = idea.get("difficulty") if is_dict else None
    category = idea.get("category") if is_dict else None
    risk_level = idea.get("risk_level") if is_dict else None
    return {
        "text": text,
        "cost": idea.get("cost") if is_dict and isinstance(idea.get("cost"), str) else None,
        "cadence": idea.get("cadence") if is_dict and isinstance(idea.get("cadence"), str) else None,
        "time_to_effect": idea.get("time_to_effect") if is_dict and isinstance(idea.get("time_to_effect"), str) else None,
        "difficulty": difficulty if difficulty in ("Easy", "Medium", "Hard") else None,
        "category": category if category in ("Cosmetic", "Lifestyle", "Clinical") else None,
        "risk_level": risk_level if risk_level in ("Low", "Medium", "High") else None,
        "product_or_method": idea.get("product_or_method")
        if is_dict and isinstance(idea.get("product_or_method"), str)
        else None,
    }


def feature_recommendation_tier(recommendation_ideas: list[Any]) -> str | None:
    """PDF-redesign addition -- one tier label per feature (not just the
    report-level 3 bucketed lists `classify_recommendations` already
    produces), for a per-feature caption on the PDF's feature pages
    (report_pdf_service.py's `_TIER_LABELS`/`_feature_flowables`) and,
    matching it, /report's ProtocolSection.tsx. Reuses the exact same
    `_classify_one` heuristic and precedence (in_clinic > otc_skincare >
    at_home, i.e. the most clinical idea present wins) rather than a new
    rule -- a feature's tier is "the highest tier any one of its own ideas
    falls into". Returns None when a feature has no recommendation ideas at
    all (nothing to caption). Accepts either the legacy bare-string or the
    FR-025 structured-object shape per idea via `recommendation_text`."""
    if not recommendation_ideas:
        return None
    tiers_present = {_classify_one(recommendation_text(idea)) for idea in recommendation_ideas}
    for tier in ("in_clinic", "otc_skincare", "at_home"):
        if tier in tiers_present:
            return tier
    return None  # unreachable in practice -- _classify_one always returns one of the three tiers above


def classify_recommendations(features: dict[str, dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Buckets every feature's recommendation_ideas into the three FR-012
    tiers, normalizing each item to the FR-025 structured-object shape
    (RecommendationItemOut) along the way -- see normalize_recommendation_item.
    First-pass keyword heuristic -- see module docstring.

    Previously also sentence-split `closing_recommendations` (the 4-
    paragraph narrative synthesis) into tier items; removed 2026-09-17
    (user-reported) -- that text is descriptive prose ("Overall facial
    harmony is well supported by balanced structural ratios..."), not a
    list of discrete suggestions, so splitting it on ". " and bucketing the
    fragments padded Treatment Protocol phases with long, paragraph-style
    fragments instead of clean, short, actionable points. Only
    `recommendation_ideas` are used now -- the AI prompt already asks for
    those as "1-3 short, complete suggestion sentences" per feature, i.e.
    already shaped like the point Treatment Protocol needs. The closing
    synthesis still gets its own dedicated display (Closing Recommendations
    page/section, via `sections["closing_recommendations"]` below) -- this
    just stops it from being double-shown as Treatment Protocol bullets."""
    tiers: dict[str, list[dict[str, Any]]] = {"at_home": [], "otc_skincare": [], "in_clinic": []}

    for feature_data in features.values():
        for idea in feature_data.get("recommendation_ideas", []) or []:
            normalized = normalize_recommendation_item(idea)
            if normalized is None:
                continue
            tiers[_classify_one(normalized["text"])].append(normalized)

    return tiers


def _measurement_result_from_dict(data: dict[str, Any] | None) -> MeasurementResult:
    """Reconstructs a MeasurementResult from the plain dict shape stored in
    FacialAnalysisResult.measurements (already round-tripped through
    JSONB) -- compute_feature_scores expects the dataclass, not a raw
    dict, since it's shared verbatim with analysis_service.py's
    dataclass-native call site."""
    if not data:
        return MeasurementResult(available=False, note="No measurement recorded.")
    return MeasurementResult(available=bool(data.get("available")), metrics=data.get("metrics"), note=data.get("note"))


def _assessment_result_from_dict(data: dict[str, Any] | None) -> AssessmentResult:
    """Same round-trip reconstruction as _measurement_result_from_dict,
    for compute_harmony_chart's `assessments` argument. drivers/sub_scores/
    overlay are intentionally not reconstructed -- compute_harmony_chart
    only ever reads `.available`/`.score`."""
    if not data:
        return AssessmentResult(available=False)
    return AssessmentResult(
        available=bool(data.get("available")), score=data.get("score"), label=data.get("label")
    )


def assemble_sections(
    measurements: dict[str, Any],
    narrative_result: dict[str, Any],
    facial_assessments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Builds the full report `sections` JSON from a completed
    FacialAnalysisResult's JSONB columns. Pure function, no I/O."""
    narrative_features = narrative_result.get("features", {})
    closing_recommendations = narrative_result.get("closing_recommendations", "")
    facial_assessments = facial_assessments or {}

    features: dict[str, Any] = {}
    for feature in ANALYSIS_FEATURES:
        narrative_entry = narrative_features.get(feature, {})
        measurement = measurements.get(feature) or {
            "available": False,
            "metrics": None,
            "note": "No measurement recorded.",
        }
        recommendation_ideas = narrative_entry.get("recommendation_ideas", []) or []
        normalized_recommendation_ideas = [
            normalized
            for idea in recommendation_ideas
            if (normalized := normalize_recommendation_item(idea)) is not None
        ]
        features[feature] = {
            # Per-feature named narrative sub-sections (e.g. hair's "Hair
            # Style"/"Hair Loss"/"Hair Health") -- see ai_narrative_service.
            # py's _FEATURE_SUBSECTIONS. Already sanitized to that feature's
            # own heading vocabulary, in canonical order, there; {} for a
            # pre-this-change narrative_result or when nothing was
            # confidently written.
            "sections": narrative_entry.get("sections") or {},
            "summary_callout": narrative_entry.get("summary_callout") or _teaser_summary_callout(measurement),
            "strengths": narrative_entry.get("strengths", ""),
            "areas_of_note": narrative_entry.get("areas_of_note", ""),
            "projected_potential": normalized_recommendation_ideas,
            "measurement": measurement,
            "recommendation_tier": feature_recommendation_tier(recommendation_ideas),
            # AI-classified named attributes for this feature (e.g. hair's
            # hairline/texture/density) -- see ai_narrative_service.py's
            # _FEATURE_ATTRIBUTE_KEYS. Already sanitized to that feature's
            # own vocabulary there; {} for a pre-this-change narrative_result
            # or when nothing was confidently assessable.
            "attributes": narrative_entry.get("attributes") or {},
        }

    # Milestone 2 (FR-018): always all 5 ASSESSMENT_CATEGORIES keys, same
    # "always report everything" convention as `features` above -- a
    # pre-Milestone-2 analysis row (facial_assessments=None) falls back to
    # an explicit all-unavailable entry per category, never a missing key.
    # Built via AssessmentResult.to_dict() (not a hand-rolled partial dict)
    # specifically so every key the API schema requires (score/label/
    # slider_position/drivers/sub_scores/overlay) is always present, even
    # as None -- a bare {"available": False, "note": ...} dict is missing
    # those and fails FacialAssessmentOut's Pydantic validation.
    _unavailable_assessment = AssessmentResult(available=False, note="Not yet analyzed.").to_dict()
    facial_assessments_out = {
        category: facial_assessments.get(category) or _unavailable_assessment for category in ASSESSMENT_CATEGORIES
    }

    measurement_objects = {
        feature: _measurement_result_from_dict(measurements.get(feature)) for feature in ANALYSIS_FEATURES
    }
    feature_scores = compute_feature_scores(measurement_objects)
    overall_score = compute_overall_score(feature_scores)

    assessment_objects = {
        category: _assessment_result_from_dict(facial_assessments_out.get(category))
        for category in ASSESSMENT_CATEGORIES
    }
    harmony_chart = compute_harmony_chart(feature_scores, assessment_objects)

    return {
        "intro": _INTRO,
        "understanding_your_results": _UNDERSTANDING_YOUR_RESULTS,
        "limitations": _LIMITATIONS,
        "features": features,
        "facial_assessments": facial_assessments_out,
        "feature_scores": {feature: score.to_dict() for feature, score in feature_scores.items()},
        "overall_score": overall_score,
        "harmony_chart": harmony_chart,
        "recommendations": classify_recommendations(narrative_features),
        "closing_recommendations": closing_recommendations,
        # report_design_spec.md v3.0 §15/§13.3 -- both come straight from
        # ai_narrative_service's own best-effort parse (already None when
        # not confidently estimable); a pre-this-change narrative_result
        # simply has no such key, so .get() naturally yields None too.
        "facial_age": narrative_result.get("facial_age"),
        "hair_loss": narrative_result.get("hair_loss"),
    }
