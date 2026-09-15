"""Facial assessment / composite-index extraction (FR-018, Milestone 2) --
pure functions, no DB/AI dependency, same independently-unit-testable split
as facial_measurement_service.py.

Sibling module, not an addition inside facial_measurement_service.py --
ANALYSIS_FEATURES/MeasurementResult there are treated as a fixed, already-
tested contract ("BR-008's 11 features are a fixed structural rule"); the
5 categories here are a different, presentation-oriented layer computed
*from* the same 478-point mesh, not a 12th "feature." Deliberately, tightly
coupled to facial_measurement_service.py's internals (its landmark index
constants, its private per-feature `_measure_*` helpers, its
LandmarkContext) via a plain module import -- reusing already-correct,
already-tested geometry rather than recomputing it is worth the coupling.

Every formula/constant below (mu/sigma reference values, score-band
cutoffs, scaling constants) is a first-pass heuristic with no ground truth
to validate against -- same posture as ASM-002/ASM-006/ASM-007/ASM-010
elsewhere in this project, recorded as `OI-5` in
docs/milestone2_requirements.md. Expect a calibration pass once real
report output can be reviewed; do not present these as clinically
validated anywhere in comments, API responses, or UI copy.
"""

from dataclasses import dataclass, field
from typing import Any

from mediapipe.tasks.python.vision.face_landmarker import FaceLandmarksConnections

from app.services import facial_measurement_service as fms
from app.services.facial_measurement_service import LandmarkContext, MeasurementResult

ASSESSMENT_CATEGORIES: tuple[str, ...] = (
    "dimorphism",
    "prototypicality",
    "proportions",
    "symmetry",
    "face_shape",
)


@dataclass(frozen=True)
class AssessmentDriver:
    """One named contributor to an assessment -- either a top driver
    (Dimorphism's overview) or one entry of a per-feature/per-region grid
    (Dimorphism's per-feature grid, Symmetry's Regional Balance)."""

    feature: str
    score: float
    label: str
    citation: str

    def to_dict(self) -> dict[str, Any]:
        return {"feature": self.feature, "score": self.score, "label": self.label, "citation": self.citation}


@dataclass(frozen=True)
class AssessmentResult:
    available: bool
    score: float | None = field(default=None)
    label: str | None = field(default=None)
    # 0-100, same value as `score` for every category here -- kept as its
    # own field since each category's slider has distinct min/max end
    # labels (e.g. "Hyper Feminine <-> Hyper Masculine"), a presentation
    # concern the frontend owns, not this module.
    slider_position: float | None = field(default=None)
    drivers: list[AssessmentDriver] | None = field(default=None)
    sub_scores: dict[str, AssessmentDriver] | None = field(default=None)
    # Normalized (0-1) coordinates for client-side diagram rendering --
    # shape/keys vary by category (see each _extract_* function below).
    overlay: dict[str, Any] | None = field(default=None)
    note: str | None = field(default=None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "score": self.score,
            "label": self.label,
            "slider_position": self.slider_position,
            "drivers": [d.to_dict() for d in self.drivers] if self.drivers is not None else None,
            "sub_scores": (
                {k: v.to_dict() for k, v in self.sub_scores.items()} if self.sub_scores is not None else None
            ),
            "overlay": self.overlay,
            "note": self.note,
        }


@dataclass(frozen=True)
class FeatureScore:
    """One 0-100 score + label per ANALYSIS_FEATURES entry -- backs the
    Dashboard's Overall Score, "Priority Features to Improve" list, and 2
    of the Harmony chart's 6 axes (Jawline, Skin). Hair/Neck are always
    unavailable here (no CV geometry exists for either at all, per
    facial_measurement_service.py's own docstring) -- never fabricated.

    `driver` is the short (1-2 word) dimension the score is actually
    measuring -- e.g. "Width" for jaw/cheeks, "Projection" for chin --
    so the Dashboard's Priority Features list can say *what* to improve,
    not just flag that a feature needs attention.

    `finding` is a short plain-language phrase for that same dimension
    (e.g. "Noticeably uneven", "Wider than typical") -- Milestone 2
    report_template.md §3.3/§3.8's "attribute line"/"Finding" content,
    shared verbatim between the Dashboard's Priority Features sub-rows
    and its Feature Evaluation table so there is exactly one place this
    phrasing is generated. `reference_value` is a formatted typical/
    benchmark value (e.g. "~60% of face width") for the same dimension,
    left None wherever no such benchmark exists -- report_template.md
    §3.8/§18: an empty cell, never a fabricated one."""

    available: bool
    score: float | None = field(default=None)
    label: str | None = field(default=None)
    note: str | None = field(default=None)
    driver: str | None = field(default=None)
    finding: str | None = field(default=None)
    reference_value: str | None = field(default=None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "score": self.score,
            "label": self.label,
            "note": self.note,
            "driver": self.driver,
            "finding": self.finding,
            "reference_value": self.reference_value,
        }


# --- shared scoring primitives ------------------------------------------


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _z_score(value: float, mu: float, sigma: float) -> float:
    if sigma <= 0:
        return 0.0
    return abs(value - mu) / sigma


def _typicality_score(z: float, scale: float = 25.0) -> float:
    """Deviation-from-typical -> 0-100. z=0 (exactly typical) -> 100;
    z=1 -> 100-scale; large z -> 0. `scale` is a tunable first-pass
    constant (OI-5), not a validated calibration."""
    return round(_clamp(100.0 - z * scale), 1)


def _band(score: float, bands: tuple[tuple[float, str], ...]) -> str:
    """`bands` sorted ascending by upper threshold; returns the first
    band's label whose threshold the score is strictly below, else the
    last (highest) band's label."""
    for threshold, label in bands:
        if score < threshold:
            return label
    return bands[-1][1]


# --- per-feature score layer (Overall Score, Priority Features list, ----
# --- 2 of the Harmony chart's 6 axes) ------------------------------------

_FEATURE_SCORE_BANDS: tuple[tuple[float, str], ...] = (
    (50.0, "Needs Attention"),
    (65.0, "Fair"),
    (80.0, "Good"),
    (101.0, "Excellent"),
)

# feature -> (metric_key, mu, sigma) against facial_measurement_service's
# existing ratios. First-pass reference ranges (OI-5), not clinically
# validated -- expect a calibration pass.
_FEATURE_REFERENCE: dict[str, tuple[str, float, float]] = {
    "eyebrows": ("symmetry_delta", 0.02, 0.02),
    "eyes": ("symmetry_delta", 0.02, 0.02),
    "nose": ("width_to_length_ratio", 1.00, 0.15),
    "cheeks": ("width_to_face_ratio", 0.60, 0.05),
    "jaw": ("width_to_face_ratio", 0.85, 0.06),
    "lips": ("width_ratio", 1.55, 0.20),
    "chin": ("projection_to_face_ratio", 0.12, 0.05),
}

_SKIN_TONE_VARIANCE_SCALE = 1.5
_EARS_SYMMETRY_SCALE = 200.0

# feature -> short (1-2 word) name of the dimension _FEATURE_REFERENCE's
# metric_key actually measures -- surfaced as FeatureScore.driver so the
# Dashboard's Priority Features list can say e.g. "Chin -- Projection"
# instead of just repeating the "Needs Attention" band label.
_FEATURE_DRIVER_LABELS: dict[str, str] = {
    "eyebrows": "Symmetry",
    "eyes": "Symmetry",
    "nose": "Proportion",
    "cheeks": "Width",
    "jaw": "Width",
    "lips": "Width",
    "chin": "Projection",
    "skin": "Tone Evenness",
    "ears": "Symmetry",
}

# feature -> (below-typical phrase, near-typical phrase, above-typical
# phrase) for the width/projection/proportion-type features, where the
# raw measured value vs. its reference `mu` has a meaningful direction
# (unlike a symmetry delta, which is a magnitude with no "direction").
# "Near typical" applies within half a sigma of `mu`. Milestone 2
# report_template.md §3.3's "plain-language attribute line" content.
_DIRECTIONAL_FINDING_PHRASES: dict[str, tuple[str, str, str]] = {
    "nose": ("Narrower relative to length", "Balanced proportion", "Wider relative to length"),
    "cheeks": ("Narrower than typical", "Close to typical width", "Wider than typical"),
    "jaw": ("Narrower than typical", "Close to typical width", "Wider than typical"),
    "lips": ("Narrower than typical", "Close to typical width", "Fuller than typical"),
    "chin": ("Less projected than typical", "Typical projection", "More projected than typical"),
}

# Magnitude-only phrasing for symmetry-delta-style metrics (eyebrows,
# eyes, ears) and skin's tone-variance score, where only "how far off"
# is meaningful, not a direction. Same 4-band shape as _FEATURE_SCORE_BANDS.
_SYMMETRY_FINDING_BANDS: tuple[tuple[float, str], ...] = (
    (50.0, "Noticeably uneven"),
    (65.0, "Slightly uneven"),
    (80.0, "Fairly even"),
    (101.0, "Well matched"),
)
_SKIN_FINDING_BANDS: tuple[tuple[float, str], ...] = (
    (50.0, "Noticeably uneven"),
    (65.0, "Somewhat uneven"),
    (80.0, "Fairly even"),
    (101.0, "Even"),
)

# feature -> a formatted, human-readable version of _FEATURE_REFERENCE's
# `mu` -- FeatureScore.reference_value. Only features with a genuine
# single reference figure get one; symmetry/skin scores have no single
# "typical value" to report and are left as None (never fabricated).
_REFERENCE_VALUE_TEXT: dict[str, str] = {
    "nose": "~1.00 width-to-length ratio",
    "cheeks": "~60% of face width",
    "jaw": "~85% of face width",
    "lips": "~1.55 width-to-eye-distance ratio",
    "chin": "~12% of face height (projection)",
}


def _directional_finding(feature: str, value: float, mu: float, sigma: float) -> str | None:
    phrases = _DIRECTIONAL_FINDING_PHRASES.get(feature)
    if phrases is None:
        return None
    below, near, above = phrases
    if sigma > 0 and abs(value - mu) < sigma * 0.5:
        return near
    return above if value > mu else below


def _score_from_reference(
    result: MeasurementResult | None, metric_key: str, mu: float, sigma: float, driver: str, feature: str
) -> FeatureScore:
    if result is None or not result.available or not result.metrics:
        return FeatureScore(available=False, note="No measurement available.")
    value = result.metrics.get(metric_key)
    if value is None:
        return FeatureScore(available=False, note="No measurement available.")
    score = _typicality_score(_z_score(value, mu, sigma))
    finding = _directional_finding(feature, value, mu, sigma)
    if finding is None:
        # eyebrows/eyes -- a symmetry delta has no meaningful direction,
        # only a magnitude, same framing as ears' finding below.
        finding = _band(score, _SYMMETRY_FINDING_BANDS)
    return FeatureScore(
        available=True,
        score=score,
        label=_band(score, _FEATURE_SCORE_BANDS),
        driver=driver,
        finding=finding,
        reference_value=_REFERENCE_VALUE_TEXT.get(feature),
    )


def _score_skin(result: MeasurementResult | None) -> FeatureScore:
    if result is None or not result.available or not result.metrics:
        return FeatureScore(available=False, note="No measurement available.")
    tone_variance = result.metrics.get("tone_variance")
    if tone_variance is None:
        return FeatureScore(available=False, note="No measurement available.")
    score = round(_clamp(100.0 - tone_variance * _SKIN_TONE_VARIANCE_SCALE), 1)
    return FeatureScore(
        available=True,
        score=score,
        label=_band(score, _FEATURE_SCORE_BANDS),
        driver=_FEATURE_DRIVER_LABELS["skin"],
        finding=_band(score, _SKIN_FINDING_BANDS),
    )


def _score_ears(result: MeasurementResult | None) -> FeatureScore:
    if result is None or not result.available or not result.metrics:
        return FeatureScore(available=False, note="No measurement available.")
    left = result.metrics.get("left_ear_to_nose_ratio")
    right = result.metrics.get("right_ear_to_nose_ratio")
    if left is None or right is None:
        return FeatureScore(available=False, note="Both ears must be measured to score ear symmetry.")
    denom = max(left, right) or 1e-6
    score = round(_clamp(100.0 - abs(left - right) / denom * _EARS_SYMMETRY_SCALE), 1)
    return FeatureScore(
        available=True,
        score=score,
        label=_band(score, _FEATURE_SCORE_BANDS),
        driver=_FEATURE_DRIVER_LABELS["ears"],
        finding=_band(score, _SYMMETRY_FINDING_BANDS),
    )


def compute_feature_scores(measurements: dict[str, MeasurementResult]) -> dict[str, FeatureScore]:
    """One FeatureScore per fms.ANALYSIS_FEATURES entry -- always all 11
    keys, mirroring extract_measurements' own convention."""
    scores: dict[str, FeatureScore] = {}
    for feature in fms.ANALYSIS_FEATURES:
        result = measurements.get(feature)
        if feature in _FEATURE_REFERENCE:
            metric_key, mu, sigma = _FEATURE_REFERENCE[feature]
            scores[feature] = _score_from_reference(
                result, metric_key, mu, sigma, _FEATURE_DRIVER_LABELS[feature], feature
            )
        elif feature == "skin":
            scores[feature] = _score_skin(result)
        elif feature == "ears":
            scores[feature] = _score_ears(result)
        else:  # hair, neck -- no CV geometry at all
            scores[feature] = FeatureScore(
                available=False, note="No dedicated CV geometry; assessed by the AI narrative instead."
            )
    return scores


# Weights for the Dashboard's aggregate Overall Score. hair/neck are always
# unavailable (no geometry) so their nominal weight is renormalized away at
# compute time; kept here only for documentation completeness.
_OVERALL_SCORE_WEIGHTS: dict[str, float] = {
    "eyebrows": 0.10,
    "eyes": 0.10,
    "nose": 0.12,
    "cheeks": 0.10,
    "jaw": 0.12,
    "lips": 0.10,
    "chin": 0.10,
    "skin": 0.08,
    "ears": 0.06,
    "hair": 0.06,
    "neck": 0.06,
}


def compute_overall_score(feature_scores: dict[str, FeatureScore]) -> float | None:
    """Weighted mean of every available feature score -- the Dashboard's
    top-line "Overall Score". None only when nothing at all is available
    (e.g. no front photo)."""
    available = {f: s for f, s in feature_scores.items() if s.available and s.score is not None}
    if not available:
        return None
    total_weight = sum(_OVERALL_SCORE_WEIGHTS.get(f, 0.0) for f in available) or 1.0
    weighted = sum(_OVERALL_SCORE_WEIGHTS.get(f, 0.0) * s.score for f, s in available.items() if s.score is not None)
    return round(weighted / total_weight, 1)


# --- Facial Assessments: Dimorphism ---------------------------------------

_DIMORPHISM_LABEL_BANDS: tuple[tuple[float, str], ...] = (
    (15.0, "Hyper Feminine"),
    (35.0, "Feminine"),
    (65.0, "Moderate"),
    (85.0, "Masculine"),
    (101.0, "Hyper Masculine"),
)

# feature -> (mu, range, inverted). `inverted=True` means a *lower*
# measured value reads as more masculine (e.g. a lower/closer-set brow).
_DIMORPHISM_REFERENCE: dict[str, tuple[float, float, bool]] = {
    "jaw": (0.85, 0.10, False),
    "nose": (1.00, 0.25, False),
    "eyebrows": (0.18, 0.06, True),
    "eyes": (0.28, 0.06, True),
    "cheeks": (0.60, 0.08, False),
    "chin": (0.12, 0.05, False),
}
_DIMORPHISM_WEIGHTS: dict[str, float] = {
    "jaw": 0.30,
    "nose": 0.20,
    "eyebrows": 0.20,
    "chin": 0.20,
    "cheeks": 0.10,
}


def _dimorphism_input_value(feature: str, metrics: dict[str, float]) -> float | None:
    if feature == "eyebrows":
        left, right = metrics.get("left_height_ratio"), metrics.get("right_height_ratio")
        return (left + right) / 2 if left is not None and right is not None else None
    if feature == "eyes":
        left, right = metrics.get("left_openness_ratio"), metrics.get("right_openness_ratio")
        return (left + right) / 2 if left is not None and right is not None else None
    metric_key = {
        "jaw": "width_to_face_ratio",
        "nose": "width_to_length_ratio",
        "cheeks": "width_to_face_ratio",
        "chin": "projection_to_face_ratio",
    }[feature]
    return metrics.get(metric_key)


def _dimorphism_sub_score(value: float, mu: float, value_range: float, inverted: bool) -> float:
    sign = -1.0 if inverted else 1.0
    return round(_clamp(50.0 + sign * (value - mu) / value_range * 50.0), 1)


def _dimorphism_citation(feature: str, value: float, label: str) -> str:
    label_lower = label.lower()
    if feature == "jaw":
        return f"{label_lower}: jaw width is {value * 100:.1f}% of face width."
    if feature == "nose":
        return f"{label_lower}: nose width-to-length ratio is {value:.2f}."
    if feature == "eyebrows":
        return f"{label_lower}: average brow height is {value * 100:.1f}% of inter-ocular distance."
    if feature == "eyes":
        return f"{label_lower}: average eye openness is {value * 100:.1f}% of inter-ocular distance."
    if feature == "cheeks":
        return f"{label_lower}: cheek width is {value * 100:.1f}% of face width."
    if feature == "chin":
        return f"{label_lower}: chin projection is {value * 100:.1f}% of face height."
    return f"{label_lower} ({value:.2f})"


def _extract_dimorphism(measurements: dict[str, MeasurementResult]) -> AssessmentResult:
    sub_scores: dict[str, AssessmentDriver] = {}
    for feature, (mu, value_range, inverted) in _DIMORPHISM_REFERENCE.items():
        result = measurements.get(feature)
        if result is None or not result.available or not result.metrics:
            continue
        value = _dimorphism_input_value(feature, result.metrics)
        if value is None:
            continue
        score = _dimorphism_sub_score(value, mu, value_range, inverted)
        label = _band(score, _DIMORPHISM_LABEL_BANDS)
        sub_scores[feature] = AssessmentDriver(
            feature=feature, score=score, label=label, citation=_dimorphism_citation(feature, value, label)
        )

    if not sub_scores:
        return AssessmentResult(available=False, note="Not enough measurements available to assess dimorphism.")

    weight_sum = sum(_DIMORPHISM_WEIGHTS.get(f, 0.0) for f in sub_scores) or 1.0
    weighted_total = sum(_DIMORPHISM_WEIGHTS.get(f, 0.0) * d.score for f, d in sub_scores.items())
    overall = round(_clamp(weighted_total / weight_sum), 1)
    overall_label = _band(overall, _DIMORPHISM_LABEL_BANDS)
    drivers = sorted(sub_scores.values(), key=lambda d: abs(d.score - 50.0), reverse=True)[:3]

    return AssessmentResult(
        available=True,
        score=overall,
        label=overall_label,
        slider_position=overall,
        drivers=drivers,
        sub_scores=sub_scores,
    )


# --- Facial Assessments: Prototypicality ----------------------------------

_PROTOTYPICALITY_LABEL_BANDS: tuple[tuple[float, str], ...] = (
    (20.0, "Highly Distinctive"),
    (40.0, "Distinctive"),
    (60.0, "Average"),
    (80.0, "Above Average"),
    (101.0, "Highly Typical"),
)
_PROTOTYPICALITY_SCALE = 25.0

# ratio name (computed specially below, not a plain metric lookup) -> (mu, sigma)
_PROTOTYPICALITY_REFERENCE: dict[str, tuple[float, float]] = {
    "eye_spacing": (0.30, 0.03),
    "nose_ratio": (1.00, 0.15),
    "lips_width": (1.55, 0.20),
    "jaw_ratio": (0.85, 0.06),
    "cheeks_ratio": (0.60, 0.05),
    "face_aspect": (0.75, 0.06),
}

# MediaPipe's documented face-oval connector set, walked into one ordered,
# closed perimeter once at import time -- never hand-list landmark indices
# for this, the canonical set is already defined upstream.
_FACE_OVAL_ORDER: tuple[int, ...] = tuple(
    [FaceLandmarksConnections.FACE_LANDMARKS_FACE_OVAL[0].start]
    + [c.end for c in FaceLandmarksConnections.FACE_LANDMARKS_FACE_OVAL]
)


def _face_outline_points(landmarks: list[Any]) -> list[list[float]]:
    """Shared by Prototypicality's "Shape Analysis" wireframe and Face
    Shape's diagram -- one normalized (x, y) point per _FACE_OVAL_ORDER
    index."""
    return [[round(landmarks[i].x, 4), round(landmarks[i].y, 4)] for i in _FACE_OVAL_ORDER]


def _prototypicality_inputs(context: LandmarkContext, measurements: dict[str, MeasurementResult]) -> dict[str, float]:
    values: dict[str, float] = {
        "face_aspect": context.face_width / context.face_height if context.face_height else 0.0,
        "eye_spacing": context.inter_ocular / context.face_width if context.face_width else 0.0,
    }
    for feature, metric_key, name in (
        ("nose", "width_to_length_ratio", "nose_ratio"),
        ("lips", "width_ratio", "lips_width"),
        ("jaw", "width_to_face_ratio", "jaw_ratio"),
        ("cheeks", "width_to_face_ratio", "cheeks_ratio"),
    ):
        result = measurements.get(feature)
        if result and result.available and result.metrics:
            value = result.metrics.get(metric_key)
            if value is not None:
                values[name] = value
    return values


def _extract_prototypicality(
    context: LandmarkContext | None, measurements: dict[str, MeasurementResult]
) -> AssessmentResult:
    if context is None:
        return AssessmentResult(available=False, note="No face landmarks detected.")

    values = _prototypicality_inputs(context, measurements)
    z_scores = {
        name: _z_score(values[name], mu, sigma)
        for name, (mu, sigma) in _PROTOTYPICALITY_REFERENCE.items()
        if name in values
    }
    if not z_scores:
        return AssessmentResult(available=False, note="Not enough measurements available.")

    avg_z = sum(z_scores.values()) / len(z_scores)
    score = _typicality_score(avg_z, scale=_PROTOTYPICALITY_SCALE)
    label = _band(score, _PROTOTYPICALITY_LABEL_BANDS)

    if score >= 80:
        note = "Your overall proportions are close to typical for this demographic reference."
    else:
        most_atypical = sorted(z_scores.items(), key=lambda item: item[1], reverse=True)[:2]
        names = ", ".join(name.replace("_", " ") for name, _ in most_atypical)
        note = (
            f"Your overall proportions sit on the distinctive side, with the most noticeable "
            f"measured variation in {names}."
        )

    return AssessmentResult(
        available=True,
        score=score,
        label=label,
        slider_position=score,
        overlay={"face_outline": _face_outline_points(context.landmarks)},
        note=note,
    )


# --- Facial Assessments: Proportions --------------------------------------

_PROPORTIONS_SCALE = 360.0
_PROPORTIONS_LABEL_BANDS: tuple[tuple[float, str], ...] = (
    (35.0, "Uneven"),
    (50.0, "Below Average"),
    (65.0, "Fair"),
    (80.0, "Good"),
    (101.0, "Excellent"),
)
_PROPORTIONS_THIRD = 1.0 / 3.0


def _extract_proportions(context: LandmarkContext | None) -> AssessmentResult:
    if context is None:
        return AssessmentResult(available=False, note="No face landmarks detected.")

    landmarks = context.landmarks
    # `hairline_y` is a documented approximation -- MediaPipe's mesh has no
    # true hairline landmark, so the forehead-top point stands in for it.
    hairline_y = landmarks[fms._FACE_TOP].y
    brow_y = (landmarks[fms._LEFT_EYEBROW_MID].y + landmarks[fms._RIGHT_EYEBROW_MID].y) / 2
    nose_base_y = landmarks[fms._NOSE_BASE].y
    chin_y = landmarks[fms._CHIN].y

    upper = brow_y - hairline_y
    middle = nose_base_y - brow_y
    lower = chin_y - nose_base_y
    total = upper + middle + lower
    if total <= 0:
        return AssessmentResult(available=False, note="Could not derive facial thirds from this photo.")

    upper_ratio, middle_ratio, lower_ratio = upper / total, middle / total, lower / total
    deviation = (
        abs(upper_ratio - _PROPORTIONS_THIRD)
        + abs(middle_ratio - _PROPORTIONS_THIRD)
        + abs(lower_ratio - _PROPORTIONS_THIRD)
    ) / 3
    score = round(_clamp(100.0 - deviation * _PROPORTIONS_SCALE), 1)
    label = _band(score, _PROPORTIONS_LABEL_BANDS)

    note = (
        f"Facial thirds measure upper {upper_ratio:.2f}, middle {middle_ratio:.2f}, "
        f"lower {lower_ratio:.2f} of total face height (reference: equal thirds)."
    )

    return AssessmentResult(
        available=True,
        score=score,
        label=label,
        slider_position=score,
        overlay={
            "upper_ratio": round(upper_ratio, 4),
            "middle_ratio": round(middle_ratio, 4),
            "lower_ratio": round(lower_ratio, 4),
            "hairline_y": round(hairline_y, 4),
            "brow_y": round(brow_y, 4),
            "nose_base_y": round(nose_base_y, 4),
            "chin_y": round(chin_y, 4),
        },
        note=note,
    )


# --- Facial Assessments: Symmetry -----------------------------------------

_SYMMETRY_SCALE = 400.0
_SYMMETRY_LABEL_BANDS: tuple[tuple[float, str], ...] = (
    (40.0, "Notable Asymmetry"),
    (60.0, "Moderate Asymmetry"),
    (75.0, "Fairly Symmetric"),
    (90.0, "Quite Symmetric"),
    (101.0, "Highly Symmetric"),
)
# Mirrored landmark-pair name -> (left index, right index). "nose" is
# included in the overall average but excluded from the 4-item "Regional
# Balance" grid, matching the reference video's own 4-region layout.
_SYMMETRY_PAIRS: dict[str, tuple[int, int]] = {
    "eyebrows": (fms._LEFT_EYEBROW_MID, fms._RIGHT_EYEBROW_MID),
    "eyes": (fms._LEFT_EYE_OUTER, fms._RIGHT_EYE_OUTER),
    "nose": (fms._NOSE_LEFT_ALA, fms._NOSE_RIGHT_ALA),
    "mouth": (fms._MOUTH_LEFT, fms._MOUTH_RIGHT),
    "jaw": (fms._JAW_LEFT, fms._JAW_RIGHT),
}
_SYMMETRY_REGIONAL_LABELS: dict[str, str] = {"eyebrows": "Brows", "eyes": "Eyes", "mouth": "Mouth", "jaw": "Jaw"}


def _extract_symmetry(context: LandmarkContext | None) -> AssessmentResult:
    if context is None:
        return AssessmentResult(available=False, note="No face landmarks detected.")

    landmarks = context.landmarks
    midline_x = (landmarks[fms._FACE_LEFT].x + landmarks[fms._FACE_RIGHT].x) / 2
    inter_ocular = context.inter_ocular or 1e-6

    pair_scores: dict[str, float] = {}
    pair_points: list[dict[str, Any]] = []
    for name, (left_idx, right_idx) in _SYMMETRY_PAIRS.items():
        left_pt, right_pt = landmarks[left_idx], landmarks[right_idx]
        left_dist = abs(left_pt.x - midline_x)
        right_dist = abs(right_pt.x - midline_x)
        asymmetry = abs(left_dist - right_dist) / inter_ocular
        score = round(_clamp(100.0 - asymmetry * _SYMMETRY_SCALE), 1)
        pair_scores[name] = score
        pair_points.append(
            {
                "feature": name,
                "left": [round(left_pt.x, 4), round(left_pt.y, 4)],
                "right": [round(right_pt.x, 4), round(right_pt.y, 4)],
            }
        )

    if not pair_scores:
        return AssessmentResult(available=False, note="Not enough landmarks to assess symmetry.")

    overall = round(sum(pair_scores.values()) / len(pair_scores), 1)
    label = _band(overall, _SYMMETRY_LABEL_BANDS)

    sub_scores = {
        _SYMMETRY_REGIONAL_LABELS[name]: AssessmentDriver(
            feature=name,
            score=score,
            label=_band(score, _SYMMETRY_LABEL_BANDS),
            citation=f"{_SYMMETRY_REGIONAL_LABELS[name]} balance score {score:.0f}/100.",
        )
        for name, score in pair_scores.items()
        if name in _SYMMETRY_REGIONAL_LABELS
    }

    return AssessmentResult(
        available=True,
        score=overall,
        label=label,
        slider_position=overall,
        sub_scores=sub_scores,
        overlay={"axis_x": round(midline_x, 4), "pairs": pair_points},
        note=f"Your overall symmetry reads as {label.lower()} ({overall:.0f}/100).",
    )


# --- Facial Assessments: Face Shape (best-effort / unconfirmed) ----------
#
# The MyFace reference video's Face Shape sub-tab was never actually opened
# in the source recording (see docs/milestone2_requirements.md §2.2/§7) --
# everything below is a first-pass placeholder built against Prototypicality
# and Symmetry's sibling pattern, flagged for a future client content
# review, and must never be presented as "matches the reference."

_FACE_SHAPE_SCALE = _PROTOTYPICALITY_SCALE


def _classify_face_shape(face_aspect: float, jaw_to_face: float, cheek_to_face: float) -> str:
    if face_aspect > 0.85:
        return "Square" if jaw_to_face > 0.90 else "Round"
    if face_aspect < 0.68:
        return "Long/Oblong"
    if (cheek_to_face - jaw_to_face) > 0.10:
        return "Heart"
    if jaw_to_face > cheek_to_face:
        return "Diamond"
    return "Oval"


def _extract_face_shape(
    context: LandmarkContext | None, measurements: dict[str, MeasurementResult]
) -> AssessmentResult:
    if context is None:
        return AssessmentResult(available=False, note="No face landmarks detected.")

    face_aspect = context.face_width / context.face_height if context.face_height else 0.0
    jaw_result = measurements.get("jaw")
    cheek_result = measurements.get("cheeks")
    jaw_to_face = jaw_result.metrics.get("width_to_face_ratio") if jaw_result and jaw_result.metrics else None
    cheek_to_face = cheek_result.metrics.get("width_to_face_ratio") if cheek_result and cheek_result.metrics else None
    if jaw_to_face is None or cheek_to_face is None:
        return AssessmentResult(available=False, note="Not enough measurements available.")

    shape = _classify_face_shape(face_aspect, jaw_to_face, cheek_to_face)
    avg_z = (
        _z_score(face_aspect, 0.75, 0.06) + _z_score(jaw_to_face, 0.85, 0.06) + _z_score(cheek_to_face, 0.60, 0.05)
    ) / 3
    score = _typicality_score(avg_z, scale=_FACE_SHAPE_SCALE)

    return AssessmentResult(
        available=True,
        score=score,
        label=shape,
        slider_position=score,
        overlay={"face_outline": _face_outline_points(context.landmarks), "shape": shape},
        note=(
            "Face shape classification is a first-pass, unconfirmed placeholder -- not validated "
            "against any client reference. Treat as provisional pending content review."
        ),
    )


# --- Harmony chart (Dashboard, 6 fixed axes) ------------------------------


def compute_harmony_chart(
    feature_scores: dict[str, FeatureScore], assessments: dict[str, AssessmentResult]
) -> dict[str, float | None]:
    """6 fixed dimension axes -- Harmony/Symmetry/Smoothness/Jawline/Skin/
    Volume -- matching the MyFace reference Dashboard's radar chart exactly
    (docs/milestone2_requirements.md §2.1). All first-pass heuristics
    (OI-5); 3 of the 6 (Harmony, Smoothness, Volume) have no independent CV
    data source anywhere in this codebase and are deliberately derived
    from other already-computed scores rather than invented from nothing --
    documented per-axis below, not a silent guess:

    - symmetry, jawline, skin: direct from the Symmetry assessment / Jaw
      and Skin feature scores.
    - smoothness: reuses the *same* Skin score -- there is no second,
      independent texture metric in this codebase (facial_measurement_
      service._measure_skin only produces one pixel-region tone-variance
      sample). Two numbers pretending to be independent would be worse
      than one honestly-labeled shared source.
    - volume: mean of Cheeks + Lips feature scores -- a loose "facial
      fullness" proxy, the weakest-grounded axis here.
    - harmony: mean of Prototypicality + Proportions + Symmetry overall
      scores -- the three assessments that are literally about balance/
      typicality, a genuine aggregate rather than an arbitrary extra input.
    """
    symmetry = assessments.get("symmetry")
    prototypicality = assessments.get("prototypicality")
    proportions = assessments.get("proportions")
    jaw = feature_scores.get("jaw")
    skin = feature_scores.get("skin")
    cheeks = feature_scores.get("cheeks")
    lips = feature_scores.get("lips")

    symmetry_score = symmetry.score if symmetry and symmetry.available else None
    jawline_score = jaw.score if jaw and jaw.available else None
    skin_score = skin.score if skin and skin.available else None
    smoothness_score = skin_score

    volume_inputs = [s.score for s in (cheeks, lips) if s and s.available and s.score is not None]
    volume_score = round(sum(volume_inputs) / len(volume_inputs), 1) if volume_inputs else None

    harmony_inputs = [
        a.score for a in (prototypicality, proportions, symmetry) if a and a.available and a.score is not None
    ]
    harmony_score = round(sum(harmony_inputs) / len(harmony_inputs), 1) if harmony_inputs else None

    return {
        "harmony": harmony_score,
        "symmetry": symmetry_score,
        "smoothness": smoothness_score,
        "jawline": jawline_score,
        "skin": skin_score,
        "volume": volume_score,
    }


# --- public entrypoints ----------------------------------------------------


def extract_facial_assessments(
    context: LandmarkContext | None, measurements: dict[str, MeasurementResult]
) -> dict[str, AssessmentResult]:
    """Always all 5 ASSESSMENT_CATEGORIES keys, mirroring
    facial_measurement_service.extract_measurements' "always all keys"
    convention. Takes an already-computed LandmarkContext (or None) rather
    than raw photos -- see extract_measurements_and_assessments() below,
    the single-pass combinator callers should actually use."""
    if context is None:
        note = "No face landmarks detected."
        return {category: AssessmentResult(available=False, note=note) for category in ASSESSMENT_CATEGORIES}

    return {
        "dimorphism": _extract_dimorphism(measurements),
        "prototypicality": _extract_prototypicality(context, measurements),
        "proportions": _extract_proportions(context),
        "symmetry": _extract_symmetry(context),
        "face_shape": _extract_face_shape(context, measurements),
    }


def extract_measurements_and_assessments(
    photos: dict[str, bytes],
) -> tuple[dict[str, MeasurementResult], dict[str, AssessmentResult]]:
    """The single-pass combinator analysis_service.run_analysis_pipeline
    should call: runs MediaPipe detection exactly once (via
    facial_measurement_service.get_landmark_context) and derives both the
    per-feature measurements and the 5 facial assessments from it. Calling
    facial_measurement_service.extract_measurements() and this module's
    extract_facial_assessments() as two separate steps would each
    independently re-run the (heavier) landmarker detection pass."""
    context = fms.get_landmark_context(photos)
    measurements = fms.measurements_from_context(context, photos)
    assessments = extract_facial_assessments(context, measurements)
    return measurements, assessments
