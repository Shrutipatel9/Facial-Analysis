"""Facial landmark measurement extraction (FR-007) -- pure functions, no
DB/AI dependency, so this is independently unit-testable with raw photo
bytes and fixture images alone, same split as photo_validation_service.py.

Uses MediaPipe's Face Landmarker (478-point mesh, Backend/var/models/
face_landmarker.task) -- a different, heavier task than the FaceDetector
already used for photo validation (bounding-box only).

Angle usage is deliberate, not an oversight: the 7 mesh-based features
below (Eyebrows, Eyes, Nose, Cheeks, Jaw, Lips, Chin) are measured from the
"front" photo only, on purpose -- these are mostly left/right SYMMETRY
comparisons, and a front-on shot is the one angle where both sides sit at
the same distance from the camera. A 3/4-turned photo foreshortens
whichever side is turned away, which would bias a symmetry measurement,
not improve it (verified empirically earlier this project: the same
synthetic-turn fixtures used to calibrate photo_validation_service.py's
pose_match check also shifted these features' own ratios by 5-25% purely
from the camera angle, not any real facial difference). Ears is the one
feature that's genuinely BETTER served by the 3/4 photos than the front
one -- a front-facing shot shows ears poorly at best, so
_measure_ears/_crop_ears use the left_3q/right_3q photos (each shows its
own side's ear clearly), falling back to front only if a side photo isn't
available.

BR-008's 11 features are a fixed structural rule, not a suggestion -- but
MediaPipe's face mesh only really covers 7 of them with real geometry
(Eyebrows, Eyes, Nose, Cheeks, Jaw, Lips, Chin). Skin gets a basic
pixel-region color/tone sample, not real texture/dermatological analysis.
Hair and Neck get no dedicated CV geometry at all -- both are outside what
the face mesh models, and are covered entirely by the AI narrative call's
own visual read of the photos (app/services/ai_narrative_service.py). This
split is a first-pass, reasonable default, not a client-specified
algorithm -- expect a tuning pass once real output is reviewed, same
posture as the photo-validation thresholds (ASM-002).
"""

import io
import math
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from mediapipe import Image as MPImage
from mediapipe import ImageFormat
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import FaceLandmarker, FaceLandmarkerOptions, RunningMode
from PIL import Image

from app.services.photo_validation_service import detect_faces

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_LANDMARKER_MODEL_PATH = _BASE_DIR / "var" / "models" / "face_landmarker.task"

# Fixed, verbatim order from FR-009/BR-008 -- "a fixed structural rule,
# not a suggestion." Do not reorder or add/remove entries.
ANALYSIS_FEATURES: tuple[str, ...] = (
    "hair",
    "eyebrows",
    "eyes",
    "nose",
    "cheeks",
    "jaw",
    "lips",
    "chin",
    "skin",
    "neck",
    "ears",
)

# Canonical MediaPipe Face Mesh landmark indices (478-point model). Widely
# documented reference points, not derived from this project's own data.
_LEFT_EYE_OUTER, _LEFT_EYE_INNER = 33, 133
_RIGHT_EYE_INNER, _RIGHT_EYE_OUTER = 362, 263
_LEFT_EYE_TOP, _LEFT_EYE_BOTTOM = 159, 145
_RIGHT_EYE_TOP, _RIGHT_EYE_BOTTOM = 386, 374
_LEFT_EYEBROW_OUTER, _LEFT_EYEBROW_MID = 70, 105
_RIGHT_EYEBROW_OUTER, _RIGHT_EYEBROW_MID = 300, 334
_NOSE_TIP, _NOSE_BRIDGE, _NOSE_BASE = 1, 6, 2
_NOSE_LEFT_ALA, _NOSE_RIGHT_ALA = 129, 358
_MOUTH_LEFT, _MOUTH_RIGHT = 61, 291
_LIP_UPPER_TOP, _LIP_LOWER_BOTTOM = 13, 14
_CHIN = 152
_JAW_LEFT, _JAW_RIGHT = 172, 397
_CHEEK_LEFT, _CHEEK_RIGHT = 50, 280
_FACE_LEFT, _FACE_RIGHT, _FACE_TOP = 234, 454, 10

# Phase 14 (Milestone 3, FR-023) additions -- same "widely documented
# reference points" posture as the block above. Iris centers (468/473) are
# always present in this model's 478-point Tasks-API output (confirmed
# empirically against this project's own fixtures -- no "refine landmarks"
# config flag exists for this API, unlike the older mediapipe.solutions
# face_mesh API).
_LEFT_EYEBROW_INNER, _RIGHT_EYEBROW_INNER = 55, 285
_LEFT_IRIS_CENTER, _RIGHT_IRIS_CENTER = 468, 473
_LIP_UPPER_OUTER_TOP, _LIP_LOWER_OUTER_BOTTOM = 0, 17
_CHIN_LEFT, _CHIN_RIGHT = 149, 378


@dataclass(frozen=True)
class MeasurementResult:
    available: bool
    metrics: dict[str, float] | None = field(default=None)
    note: str | None = field(default=None)

    def to_dict(self) -> dict[str, Any]:
        return {"available": self.available, "metrics": self.metrics, "note": self.note}


@dataclass(frozen=True)
class LandmarkContext:
    """The MediaPipe Face Landmarker output plus the handful of face-level
    reference distances every per-feature formula in this module builds on
    -- factored out of extract_measurements (Milestone 2, FR-018) so
    facial_assessment_service.py's new composite indices (dimorphism,
    prototypicality, proportions, symmetry, face shape) can reuse the same
    detection pass instead of re-running the landmarker a second time per
    analysis."""

    landmarks: list[Any]
    inter_ocular: float
    face_width: float
    face_height: float
    scale: float  # inter_ocular, floored away from zero -- the shared per-feature ratio denominator
    rgb_array: np.ndarray


def get_landmark_context(photos: dict[str, bytes]) -> LandmarkContext | None:
    """Runs the landmarker once on the front photo. Returns None when no
    front photo is uploaded or no face is detected -- every caller
    (extract_measurements below, and facial_assessment_service.py's
    extract_facial_assessments) treats None the same way: everything it
    would have computed becomes unavailable, never a fabricated value."""
    front_bytes = photos.get("front")
    if front_bytes is None:
        return None

    image = Image.open(io.BytesIO(front_bytes)).convert("RGB")
    rgb_array = np.asarray(image, dtype=np.uint8)
    mp_image = MPImage(image_format=ImageFormat.SRGB, data=rgb_array)
    result = _get_landmarker().detect(mp_image)
    if not result.face_landmarks:
        return None

    landmarks = result.face_landmarks[0]
    inter_ocular = _distance(landmarks, _LEFT_EYE_INNER, _RIGHT_EYE_INNER)
    face_width = _distance(landmarks, _FACE_LEFT, _FACE_RIGHT)
    face_height = _distance(landmarks, _FACE_TOP, _CHIN)
    scale = inter_ocular if inter_ocular > 0 else 1e-6
    return LandmarkContext(
        landmarks=landmarks,
        inter_ocular=inter_ocular,
        face_width=face_width,
        face_height=face_height,
        scale=scale,
        rgb_array=rgb_array,
    )


@lru_cache
def _get_landmarker() -> FaceLandmarker:
    base_options = BaseOptions(model_asset_path=str(_LANDMARKER_MODEL_PATH))
    options = FaceLandmarkerOptions(
        base_options=base_options,
        running_mode=RunningMode.IMAGE,
        num_faces=1,
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
    )
    return FaceLandmarker.create_from_options(options)


def _point(landmarks: list[Any], index: int) -> tuple[float, float]:
    lm = landmarks[index]
    return (lm.x, lm.y)


def _distance(landmarks: list[Any], i: int, j: int) -> float:
    ax, ay = _point(landmarks, i)
    bx, by = _point(landmarks, j)
    return math.hypot(ax - bx, ay - by)


def _tilt_degrees(landmarks: list[Any], near_index: int, far_index: int) -> float:
    """Vertical tilt of the line from `near` to `far`, in degrees. Uses
    abs(dx) as the run deliberately, not signed dx -- a signed-dx version
    would flip sign between mirrored left/right pairs, since the "outer"
    point sits on the smaller-x side of "inner" for the left eye/brow but
    the larger-x side for the right one (verified empirically this phase:
    a naive atan2(dy, dx) reported opposite-sign tilts for two sides with
    the same real-world tilt). Positive = `far` is higher (smaller y) than
    `near`; range is always (-90, 90) by construction."""
    nx, ny = _point(landmarks, near_index)
    fx, fy = _point(landmarks, far_index)
    run = abs(fx - nx) or 1e-9
    return math.degrees(math.atan2(-(fy - ny), run))


def _angle_degrees(landmarks: list[Any], a_index: int, vertex_index: int, c_index: int) -> float:
    """Interior angle (0-180 degrees) at `vertex`, between rays
    vertex->a and vertex->c. For frontal-plane contour angles only (e.g.
    the jaw's gonial-angle proxy) -- deliberately NOT used for a
    nasolabial/nasofrontal angle, which degenerates to ~178-180 degrees
    when computed from front-only (x, y) landmarks (verified empirically
    this phase: those points sit close to the face's vertical midline in a
    frontal projection, so the angle carries no real signal from this
    photo angle alone)."""
    vx, vy = _point(landmarks, vertex_index)
    ax, ay = _point(landmarks, a_index)
    cx, cy = _point(landmarks, c_index)
    v1x, v1y = ax - vx, ay - vy
    v2x, v2y = cx - vx, cy - vy
    m1, m2 = math.hypot(v1x, v1y), math.hypot(v2x, v2y)
    if m1 == 0 or m2 == 0:
        return 0.0
    cos_angle = max(-1.0, min(1.0, (v1x * v2x + v1y * v2y) / (m1 * m2)))
    return math.degrees(math.acos(cos_angle))


def extract_measurements(photos: dict[str, bytes]) -> dict[str, MeasurementResult]:
    """`photos` maps angle id -> raw image bytes (at minimum "front", which
    the 7 mesh-based features and Skin require; "left_3q"/"right_3q" if
    available are used by Ears -- see this module's docstring for why).
    Returns a dict keyed by every entry in ANALYSIS_FEATURES -- always all
    11 keys, mirroring photo_validation_service.validate_photo's "always
    report everything" convention.

    Runs its own get_landmark_context() detection pass. A caller that also
    needs facial_assessment_service.py's composite indices from the same
    photos should call get_landmark_context() once itself and pass the
    result to measurements_from_context() below and to
    facial_assessment_service.extract_facial_assessments(), instead of
    calling this function separately -- see
    facial_assessment_service.extract_measurements_and_assessments(), the
    single-pass combinator analysis_service.py actually uses."""
    context = get_landmark_context(photos)
    return measurements_from_context(context, photos)


def measurements_from_context(
    context: LandmarkContext | None, photos: dict[str, bytes]
) -> dict[str, MeasurementResult]:
    """The body of extract_measurements(), taking an already-computed (or
    None) LandmarkContext instead of running detection itself -- the piece
    that actually makes single-pass sharing with facial_assessment_service.py
    possible."""
    if context is None:
        note = "No front-angle photo available." if photos.get("front") is None else "No face landmarks detected."
        unavailable = MeasurementResult(False, note=note)
        return {feature: unavailable for feature in ANALYSIS_FEATURES}

    landmarks, scale = context.landmarks, context.scale

    measurements: dict[str, MeasurementResult] = {
        "eyebrows": _measure_eyebrows(landmarks, scale),
        "eyes": _measure_eyes(landmarks, scale, context.face_width),
        "nose": _measure_nose(landmarks, scale),
        "cheeks": _measure_cheeks(landmarks, context.face_width, context.face_height),
        "jaw": _measure_jaw(landmarks, context.face_width, scale),
        "lips": _measure_lips(landmarks, scale),
        "chin": _measure_chin(landmarks, context.face_height),
        "skin": _measure_skin(context.rgb_array, landmarks),
        "ears": _measure_ears(photos),
        "hair": MeasurementResult(
            False, note="No dedicated CV geometry; covered by the AI's visual read of the photos."
        ),
        "neck": MeasurementResult(
            False, note="No dedicated CV geometry; covered by the AI's visual read of the photos."
        ),
    }
    return measurements


def _measure_eyebrows(landmarks: list[Any], scale: float) -> MeasurementResult:
    left_height = _distance(landmarks, _LEFT_EYEBROW_MID, _LEFT_EYE_TOP) / scale
    right_height = _distance(landmarks, _RIGHT_EYEBROW_MID, _RIGHT_EYE_TOP) / scale
    # Phase 14 (FR-023) additions. Length here is inner-to-outer brow span,
    # an approximation of "Tail Length" -- only 3 points per brow exist in
    # this module, not a full brow contour, so true tail curvature isn't
    # derivable. Brow Shape/Thickness/Position/Lift, Start/End Point, and
    # Tail Drop are deliberately not added -- they need finer brow-contour
    # landmarks than the 3 points already extracted here.
    left_tilt = _tilt_degrees(landmarks, _LEFT_EYEBROW_INNER, _LEFT_EYEBROW_OUTER)
    right_tilt = _tilt_degrees(landmarks, _RIGHT_EYEBROW_INNER, _RIGHT_EYEBROW_OUTER)
    interbrow = _distance(landmarks, _LEFT_EYEBROW_INNER, _RIGHT_EYEBROW_INNER) / scale
    left_length = _distance(landmarks, _LEFT_EYEBROW_INNER, _LEFT_EYEBROW_OUTER) / scale
    right_length = _distance(landmarks, _RIGHT_EYEBROW_INNER, _RIGHT_EYEBROW_OUTER) / scale
    return MeasurementResult(
        True,
        metrics={
            "left_height_ratio": round(left_height, 4),
            "right_height_ratio": round(right_height, 4),
            "symmetry_delta": round(abs(left_height - right_height), 4),
            "left_tilt_deg": round(left_tilt, 2),
            "right_tilt_deg": round(right_tilt, 2),
            "interbrow_distance_ratio": round(interbrow, 4),
            "left_length_ratio": round(left_length, 4),
            "right_length_ratio": round(right_length, 4),
        },
    )


def _measure_eyes(landmarks: list[Any], scale: float, face_width: float) -> MeasurementResult:
    left_width = _distance(landmarks, _LEFT_EYE_OUTER, _LEFT_EYE_INNER) / scale
    right_width = _distance(landmarks, _RIGHT_EYE_INNER, _RIGHT_EYE_OUTER) / scale
    left_openness = _distance(landmarks, _LEFT_EYE_TOP, _LEFT_EYE_BOTTOM) / scale
    right_openness = _distance(landmarks, _RIGHT_EYE_TOP, _RIGHT_EYE_BOTTOM) / scale
    # Phase 14 (FR-023) additions. Intercanthal/interpupillary distance are
    # normalized by face_width, not `scale` -- `scale` IS inter_ocular (the
    # inner-canthi distance), so normalizing intercanthal distance by it
    # would be a trivial ~1.0 constant; face_width matches the "how wide is
    # X relative to the whole face" convention used elsewhere (cheeks/jaw).
    # Scleral Show/Color, Limbal Ring, Under-Eye conditions, and Epicanthic
    # Fold are deliberately not added here -- they need pixel/texture
    # analysis this module has no basis for, not a landmark ratio.
    left_canthal_tilt = _tilt_degrees(landmarks, _LEFT_EYE_INNER, _LEFT_EYE_OUTER)
    right_canthal_tilt = _tilt_degrees(landmarks, _RIGHT_EYE_INNER, _RIGHT_EYE_OUTER)
    intercanthal = _distance(landmarks, _LEFT_EYE_INNER, _RIGHT_EYE_INNER) / face_width if face_width else 0.0
    interpupillary = (
        _distance(landmarks, _LEFT_IRIS_CENTER, _RIGHT_IRIS_CENTER) / face_width if face_width else 0.0
    )
    return MeasurementResult(
        True,
        metrics={
            "left_width_ratio": round(left_width, 4),
            "right_width_ratio": round(right_width, 4),
            "left_openness_ratio": round(left_openness, 4),
            "right_openness_ratio": round(right_openness, 4),
            "symmetry_delta": round(abs(left_width - right_width), 4),
            "left_canthal_tilt_deg": round(left_canthal_tilt, 2),
            "right_canthal_tilt_deg": round(right_canthal_tilt, 2),
            "left_shape_ratio": round(left_openness / left_width, 4) if left_width else 0.0,
            "right_shape_ratio": round(right_openness / right_width, 4) if right_width else 0.0,
            "intercanthal_to_face_width_ratio": round(intercanthal, 4),
            "interpupillary_distance_ratio": round(interpupillary, 4),
        },
    )


def _measure_nose(landmarks: list[Any], scale: float) -> MeasurementResult:
    width = _distance(landmarks, _NOSE_LEFT_ALA, _NOSE_RIGHT_ALA) / scale
    length = _distance(landmarks, _NOSE_BRIDGE, _NOSE_BASE) / scale
    # Phase 14 (FR-023): tip position along the bridge-to-base line (a 2D
    # proxy for tip projection/rotation) and columella lateral deviation
    # from the face midline (a proxy for columella/septum alignment).
    # Nasofrontal Angle and Nasolabial Angle are deliberately NOT added --
    # verified empirically this phase that both collapse to ~178-180
    # degrees from a front-only photo (the candidate landmark triples sit
    # too close to the face's vertical midline in a frontal projection to
    # carry any real signal), which would be fabricated precision, not a
    # genuine measurement.
    bridge_to_base = _distance(landmarks, _NOSE_BRIDGE, _NOSE_BASE)
    tip_to_bridge = _distance(landmarks, _NOSE_TIP, _NOSE_BRIDGE)
    tip_position = tip_to_bridge / bridge_to_base if bridge_to_base else 0.0
    midline_x = (landmarks[_FACE_LEFT].x + landmarks[_FACE_RIGHT].x) / 2
    columella_deviation = abs(landmarks[_NOSE_TIP].x - midline_x) / scale
    return MeasurementResult(
        True,
        metrics={
            "width_ratio": round(width, 4),
            "length_ratio": round(length, 4),
            "width_to_length_ratio": round(width / length, 4) if length else 0.0,
            "tip_position_ratio": round(tip_position, 4),
            "columella_deviation_ratio": round(columella_deviation, 4),
        },
    )


def _measure_cheeks(landmarks: list[Any], face_width: float, face_height: float) -> MeasurementResult:
    width = _distance(landmarks, _CHEEK_LEFT, _CHEEK_RIGHT) / face_width if face_width else 0.0
    # Phase 14 (FR-023) additions. Cheekbone Projection/Shape, Mid-Cheek
    # Fullness, and Under-Cheek Hollowing are deliberately not added --
    # they need depth/contour or texture information a front-only 2D mesh
    # doesn't expose confidently.
    jaw_width = _distance(landmarks, _JAW_LEFT, _JAW_RIGHT)
    cheek_to_jaw = _distance(landmarks, _CHEEK_LEFT, _CHEEK_RIGHT) / jaw_width if jaw_width else 0.0
    left_eye_bottom_y = landmarks[_LEFT_EYE_BOTTOM].y
    right_eye_bottom_y = landmarks[_RIGHT_EYE_BOTTOM].y
    cheekbone_height = (
        ((left_eye_bottom_y + right_eye_bottom_y) / 2) - ((landmarks[_CHEEK_LEFT].y + landmarks[_CHEEK_RIGHT].y) / 2)
    ) / face_height if face_height else 0.0
    midline_x = (landmarks[_FACE_LEFT].x + landmarks[_FACE_RIGHT].x) / 2
    left_to_midline = abs(landmarks[_CHEEK_LEFT].x - midline_x)
    right_to_midline = abs(landmarks[_CHEEK_RIGHT].x - midline_x)
    symmetry_delta = abs(left_to_midline - right_to_midline) / face_width if face_width else 0.0
    return MeasurementResult(
        True,
        metrics={
            "width_to_face_ratio": round(width, 4),
            "cheek_to_jaw_ratio": round(cheek_to_jaw, 4),
            "cheekbone_height_ratio": round(cheekbone_height, 4),
            "symmetry_delta": round(symmetry_delta, 4),
        },
    )


def _measure_jaw(landmarks: list[Any], face_width: float, scale: float) -> MeasurementResult:
    width = _distance(landmarks, _JAW_LEFT, _JAW_RIGHT) / face_width if face_width else 0.0
    # Phase 14 (FR-023) additions. The two contour-angle metrics are a
    # frontal-plane proxy for jaw taper/gonial angle, not a lateral
    # cephalometric measurement -- a true gonial angle is measured in
    # profile; this captures how the jaw corner reads from the front,
    # which correlates with but is not equal to the clinical angle. Jaw
    # Shape (Side) and Jawline Definition/Contrast are deliberately not
    # added -- profile-only or texture-only concepts this module has no
    # basis for from a single front photo.
    cheek_width = _distance(landmarks, _CHEEK_LEFT, _CHEEK_RIGHT)
    jaw_width = _distance(landmarks, _JAW_LEFT, _JAW_RIGHT)
    jaw_to_cheek = jaw_width / cheek_width if cheek_width else 0.0
    left_contour_angle = _angle_degrees(landmarks, _CHEEK_LEFT, _JAW_LEFT, _CHIN)
    right_contour_angle = _angle_degrees(landmarks, _CHEEK_RIGHT, _JAW_RIGHT, _CHIN)
    left_length = _distance(landmarks, _JAW_LEFT, _CHIN)
    right_length = _distance(landmarks, _JAW_RIGHT, _CHIN)
    length = ((left_length + right_length) / 2) / scale
    flare_symmetry_delta = abs(left_length - right_length) / scale
    return MeasurementResult(
        True,
        metrics={
            "width_to_face_ratio": round(width, 4),
            "jaw_to_cheek_ratio": round(jaw_to_cheek, 4),
            "left_jaw_contour_angle_deg": round(left_contour_angle, 2),
            "right_jaw_contour_angle_deg": round(right_contour_angle, 2),
            "length_ratio": round(length, 4),
            "flare_symmetry_delta": round(flare_symmetry_delta, 4),
        },
    )


def _measure_lips(landmarks: list[Any], scale: float) -> MeasurementResult:
    width = _distance(landmarks, _MOUTH_LEFT, _MOUTH_RIGHT) / scale
    fullness = _distance(landmarks, _LIP_UPPER_TOP, _LIP_LOWER_BOTTOM) / scale
    # Phase 14 (FR-023) additions. Cupid's Bow, Philtrum Shape, Vermilion
    # Definition, and Gloss/Hydration are deliberately not added -- they
    # need contour/texture points or pixel analysis not available from the
    # 4 mouth landmarks already extracted here.
    upper_thickness = _distance(landmarks, _LIP_UPPER_OUTER_TOP, _LIP_UPPER_TOP) / scale
    lower_thickness = _distance(landmarks, _LIP_LOWER_BOTTOM, _LIP_LOWER_OUTER_BOTTOM) / scale
    upper_to_lower = upper_thickness / lower_thickness if lower_thickness else 0.0
    commissure_tilt = _tilt_degrees(landmarks, _MOUTH_LEFT, _MOUTH_RIGHT)
    return MeasurementResult(
        True,
        metrics={
            "width_ratio": round(width, 4),
            "fullness_ratio": round(fullness, 4),
            "upper_lip_thickness_ratio": round(upper_thickness, 4),
            "lower_lip_thickness_ratio": round(lower_thickness, 4),
            "upper_to_lower_ratio": round(upper_to_lower, 4),
            "oral_commissure_tilt_deg": round(commissure_tilt, 2),
        },
    )


def _measure_chin(landmarks: list[Any], face_height: float) -> MeasurementResult:
    projection = (
        _distance(landmarks, _LIP_LOWER_BOTTOM, _CHIN) / face_height if face_height else 0.0
    )
    # Phase 14 (FR-023) additions. Shape, Contour, Fullness, Dimple, and
    # Inclination are deliberately not added -- Inclination is a
    # profile-only concept (same front-only-photo collapse risk as the
    # excluded nasolabial/nasofrontal angles), and the rest need texture or
    # dense-contour analysis this module has no basis for.
    width = _distance(landmarks, _CHIN_LEFT, _CHIN_RIGHT) / face_height if face_height else 0.0
    left_length = _distance(landmarks, _CHIN_LEFT, _CHIN)
    right_length = _distance(landmarks, _CHIN_RIGHT, _CHIN)
    symmetry_delta = abs(left_length - right_length) / face_height if face_height else 0.0
    return MeasurementResult(
        True,
        metrics={
            "projection_to_face_ratio": round(projection, 4),
            "width_ratio": round(width, 4),
            "symmetry_delta": round(symmetry_delta, 4),
        },
    )


def _measure_skin(rgb_array: np.ndarray, landmarks: list[Any]) -> MeasurementResult:
    """Basic pixel-region color/tone sample from a forehead patch -- not
    real texture/dermatological analysis, a simplified heuristic (same
    honesty framing as the photo-validation occlusion check)."""
    height, width, _ = rgb_array.shape
    fx, fy = _point(landmarks, _FACE_TOP)
    cx, cy = int(fx * width), int(fy * height)
    half = max(4, width // 40)
    y0, y1 = max(0, cy - half), min(height, cy + half)
    x0, x1 = max(0, cx - half), min(width, cx + half)
    patch = rgb_array[y0:y1, x0:x1]
    if patch.size == 0:
        return MeasurementResult(False, note="Could not sample a forehead region for skin tone.")
    mean_rgb = patch.reshape(-1, 3).mean(axis=0)
    tone_variance = float(patch.reshape(-1, 3).std())
    return MeasurementResult(
        True,
        metrics={
            "mean_r": round(float(mean_rgb[0]), 2),
            "mean_g": round(float(mean_rgb[1]), 2),
            "mean_b": round(float(mean_rgb[2]), 2),
            "tone_variance": round(tone_variance, 2),
        },
        note="Basic pixel-region sample, not clinical texture/dermatological analysis.",
    )


# BlazeFace short-range fixed keypoint order: right_eye, left_eye,
# nose_tip, mouth_center, right_ear_tragion, left_ear_tragion (subject's
# own right/left, confirmed empirically -- see photo_validation_service.py).
_KP_RIGHT_EYE, _KP_LEFT_EYE, _KP_NOSE_TIP = 0, 1, 2
_KP_RIGHT_EAR, _KP_LEFT_EAR = 4, 5


def _measure_one_ear(photo_bytes: bytes, side: str) -> float | None:
    """One side's ear-tragion position, expressed as a ratio to that SAME
    photo's own eye-to-nose distance -- deliberately never compared across
    two different photos' pixel coordinates (a left_3q and a right_3q shot
    differ in framing/distance/turn angle, so raw pixel distances from one
    aren't meaningfully comparable to the other; the same-photo ratio is)."""
    image = Image.open(io.BytesIO(photo_bytes)).convert("RGB")
    detection_result = detect_faces(image)
    if not detection_result.detections:
        return None
    keypoints = detection_result.detections[0].keypoints
    if len(keypoints) < 6:
        return None
    width, height = image.size
    ear = keypoints[_KP_RIGHT_EAR if side == "right" else _KP_LEFT_EAR]
    eye = keypoints[_KP_RIGHT_EYE if side == "right" else _KP_LEFT_EYE]
    nose = keypoints[_KP_NOSE_TIP]
    scale = math.hypot((eye.x - nose.x) * width, (eye.y - nose.y) * height) or 1e-6
    ear_to_nose = math.hypot((ear.x - nose.x) * width, (ear.y - nose.y) * height)
    return ear_to_nose / scale


def _measure_ears(photos: dict[str, bytes]) -> MeasurementResult:
    """Measures each ear from its own 3/4-angle photo (left_3q shows the
    left ear clearly, right_3q the right) rather than the front photo --
    see this module's docstring for why front-facing shots show ears
    poorly. Falls back to the front photo per side if that angle wasn't
    uploaded, so this still degrades gracefully instead of going
    unavailable. Reuses the lightweight FaceDetector already built for
    photo validation -- no dedicated ear-landmark model exists here."""
    left_source = photos.get("left_3q") or photos.get("front")
    right_source = photos.get("right_3q") or photos.get("front")

    metrics: dict[str, float] = {}
    if left_source is not None:
        value = _measure_one_ear(left_source, "left")
        if value is not None:
            metrics["left_ear_to_nose_ratio"] = round(value, 4)
    if right_source is not None:
        value = _measure_one_ear(right_source, "right")
        if value is not None:
            metrics["right_ear_to_nose_ratio"] = round(value, 4)

    if not metrics:
        return MeasurementResult(False, note="No face detected for ear keypoints.")
    return MeasurementResult(
        True,
        metrics=metrics,
        note=(
            "Each side measured from its own 3/4-angle photo where available (better ear visibility "
            "than a front-facing shot); derived from face-detector ear-tragion keypoints, not a "
            "dedicated ear landmark model. Left and right are not directly comparable to each other "
            "since they come from two different photos."
        ),
    )


# --- Feature crop extraction (report imagery only, not used by
# extract_measurements()) -----------------------------------------------
#
# Landmark index groups per feature, reusing the same canonical indices
# already defined above. A reasonable first-pass heuristic bounding-box
# crop, not a precision segmentation model -- expect a tuning pass, same
# posture as the measurement formulas themselves (see module docstring).

_EYEBROW_CROP_INDICES = (
    _LEFT_EYEBROW_OUTER,
    _LEFT_EYEBROW_MID,
    _RIGHT_EYEBROW_OUTER,
    _RIGHT_EYEBROW_MID,
    _LEFT_EYE_TOP,
    _RIGHT_EYE_TOP,
)
_EYES_CROP_INDICES = (
    _LEFT_EYE_OUTER,
    _LEFT_EYE_INNER,
    _RIGHT_EYE_INNER,
    _RIGHT_EYE_OUTER,
    _LEFT_EYE_TOP,
    _LEFT_EYE_BOTTOM,
    _RIGHT_EYE_TOP,
    _RIGHT_EYE_BOTTOM,
)
_NOSE_CROP_INDICES = (_NOSE_TIP, _NOSE_BRIDGE, _NOSE_BASE, _NOSE_LEFT_ALA, _NOSE_RIGHT_ALA)
_CHEEKS_CROP_INDICES = (_CHEEK_LEFT, _CHEEK_RIGHT, _NOSE_BASE, _MOUTH_LEFT, _MOUTH_RIGHT)
_JAW_CROP_INDICES = (_JAW_LEFT, _JAW_RIGHT, _CHIN, _FACE_LEFT, _FACE_RIGHT)
_LIPS_CROP_INDICES = (_MOUTH_LEFT, _MOUTH_RIGHT, _LIP_UPPER_TOP, _LIP_LOWER_BOTTOM)
_CHIN_CROP_INDICES = (_CHIN, _LIP_LOWER_BOTTOM, _JAW_LEFT, _JAW_RIGHT)

_CROP_JPEG_QUALITY = 85


def _encode_jpeg(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=_CROP_JPEG_QUALITY)
    return buffer.getvalue()


def _box_from_points(
    points_px: list[tuple[float, float]], width: int, height: int, pad_frac: float, min_size_frac: float
) -> tuple[int, int, int, int]:
    xs = [p[0] for p in points_px]
    ys = [p[1] for p in points_px]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    pad_x, pad_y = (x1 - x0) * pad_frac, (y1 - y0) * pad_frac
    x0, x1 = x0 - pad_x, x1 + pad_x
    y0, y1 = y0 - pad_y, y1 + pad_y

    min_w, min_h = width * min_size_frac, height * min_size_frac
    if (x1 - x0) < min_w:
        cx = (x0 + x1) / 2
        x0, x1 = cx - min_w / 2, cx + min_w / 2
    if (y1 - y0) < min_h:
        cy = (y0 + y1) / 2
        y0, y1 = cy - min_h / 2, cy + min_h / 2

    return (
        max(0, int(x0)),
        max(0, int(y0)),
        min(width, int(x1)),
        min(height, int(y1)),
    )


def _crop_from_landmarks(
    image: Image.Image, landmarks: list[Any], indices: tuple[int, ...], pad_frac: float, min_size_frac: float = 0.14
) -> bytes:
    width, height = image.size
    points_px = [(landmarks[i].x * width, landmarks[i].y * height) for i in indices]
    box = _box_from_points(points_px, width, height, pad_frac, min_size_frac)
    return _encode_jpeg(image.crop(box))


def extract_feature_crops(photos: dict[str, bytes]) -> dict[str, bytes | None]:
    """Best-effort cropped region per feature from the front-angle photo,
    for report imagery only (report_service.py) -- independent of
    extract_measurements(), which is why this re-runs landmark detection
    rather than sharing state: measurements are computed once during the
    analysis pipeline (Phase 4) and only the resulting ratios are
    persisted, not raw landmarks, so report generation (Phase 5) needs its
    own detection pass on the already-stored photo.

    Returns None per feature where no reasonable crop can be derived (no
    front photo, no face detected, or -- for Ears -- no detector
    keypoints). Hair and Neck use a coarse image-region approximation
    (above/below the face box) rather than landmark points, since neither
    is covered by the face mesh at all.
    """
    front_bytes = photos.get("front")
    if front_bytes is None:
        return dict.fromkeys(ANALYSIS_FEATURES)

    image = Image.open(io.BytesIO(front_bytes)).convert("RGB")
    width, height = image.size
    rgb_array = np.asarray(image, dtype=np.uint8)
    mp_image = MPImage(image_format=ImageFormat.SRGB, data=rgb_array)
    result = _get_landmarker().detect(mp_image)
    if not result.face_landmarks:
        return dict.fromkeys(ANALYSIS_FEATURES)
    landmarks = result.face_landmarks[0]

    face_top_y = landmarks[_FACE_TOP].y * height
    face_left_x = landmarks[_FACE_LEFT].x * width
    face_right_x = landmarks[_FACE_RIGHT].x * width
    chin_y = landmarks[_CHIN].y * height

    crops: dict[str, bytes | None] = {
        "eyebrows": _crop_from_landmarks(image, landmarks, _EYEBROW_CROP_INDICES, pad_frac=0.7),
        "eyes": _crop_from_landmarks(image, landmarks, _EYES_CROP_INDICES, pad_frac=0.6),
        "nose": _crop_from_landmarks(image, landmarks, _NOSE_CROP_INDICES, pad_frac=0.4),
        "cheeks": _crop_from_landmarks(image, landmarks, _CHEEKS_CROP_INDICES, pad_frac=0.2),
        "jaw": _crop_from_landmarks(image, landmarks, _JAW_CROP_INDICES, pad_frac=0.15),
        "lips": _crop_from_landmarks(image, landmarks, _LIPS_CROP_INDICES, pad_frac=0.6),
        "chin": _crop_from_landmarks(image, landmarks, _CHIN_CROP_INDICES, pad_frac=0.35),
        "skin": _encode_jpeg(
            image.crop(_box_from_points([(face_left_x, face_top_y)], width, height, pad_frac=0.0, min_size_frac=0.22))
        ),
        # Hair: image-top region down to the hairline landmark -- no face-mesh coverage at all.
        "hair": (
            _encode_jpeg(
                image.crop((max(0, int(face_left_x)), 0, min(width, int(face_right_x)), int(face_top_y) + 10))
            )
            if face_top_y > 4
            else None
        ),
        # Neck: below the chin down to the image bottom -- likewise no face-mesh coverage.
        "neck": _encode_jpeg(
            image.crop((max(0, int(face_left_x)), int(chin_y) - 10, min(width, int(face_right_x)), height))
        )
        if chin_y < height - 4
        else None,
        "ears": _crop_ears(image, front_bytes),
    }
    return crops


def _crop_ears(image: Image.Image, front_bytes: bytes) -> bytes | None:
    """Union of both ear-tragion keypoints from the face detector (same
    source as _measure_ears) -- front-facing photos show ears poorly at
    best, an accepted limitation rather than a dedicated ear model."""
    detection_result = detect_faces(image)
    if not detection_result.detections:
        return None
    keypoints = detection_result.detections[0].keypoints
    if len(keypoints) < 6:
        return None
    right_ear, left_ear = keypoints[4], keypoints[5]
    width, height = image.size
    points_px = [(right_ear.x * width, right_ear.y * height), (left_ear.x * width, left_ear.y * height)]
    box = _box_from_points(points_px, width, height, pad_frac=0.8, min_size_frac=0.16)
    return _encode_jpeg(image.crop(box))
