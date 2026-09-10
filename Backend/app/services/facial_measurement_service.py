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


@dataclass(frozen=True)
class MeasurementResult:
    available: bool
    metrics: dict[str, float] | None = field(default=None)
    note: str | None = field(default=None)

    def to_dict(self) -> dict[str, Any]:
        return {"available": self.available, "metrics": self.metrics, "note": self.note}


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


def extract_measurements(photos: dict[str, bytes]) -> dict[str, MeasurementResult]:
    """`photos` maps angle id -> raw image bytes (at minimum "front", which
    the 7 mesh-based features and Skin require; "left_3q"/"right_3q" if
    available are used by Ears -- see this module's docstring for why).
    Returns a dict keyed by every entry in ANALYSIS_FEATURES -- always all
    11 keys, mirroring photo_validation_service.validate_photo's "always
    report everything" convention."""
    front_bytes = photos.get("front")
    if front_bytes is None:
        unavailable = MeasurementResult(False, note="No front-angle photo available.")
        return {feature: unavailable for feature in ANALYSIS_FEATURES}

    image = Image.open(io.BytesIO(front_bytes)).convert("RGB")
    rgb_array = np.asarray(image, dtype=np.uint8)
    mp_image = MPImage(image_format=ImageFormat.SRGB, data=rgb_array)
    result = _get_landmarker().detect(mp_image)

    if not result.face_landmarks:
        unavailable = MeasurementResult(False, note="No face landmarks detected.")
        return {feature: unavailable for feature in ANALYSIS_FEATURES}

    landmarks = result.face_landmarks[0]

    inter_ocular = _distance(landmarks, _LEFT_EYE_INNER, _RIGHT_EYE_INNER)
    face_width = _distance(landmarks, _FACE_LEFT, _FACE_RIGHT)
    face_height = _distance(landmarks, _FACE_TOP, _CHIN)
    scale = inter_ocular if inter_ocular > 0 else 1e-6

    measurements: dict[str, MeasurementResult] = {
        "eyebrows": _measure_eyebrows(landmarks, scale),
        "eyes": _measure_eyes(landmarks, scale),
        "nose": _measure_nose(landmarks, scale),
        "cheeks": _measure_cheeks(landmarks, face_width),
        "jaw": _measure_jaw(landmarks, face_width),
        "lips": _measure_lips(landmarks, scale),
        "chin": _measure_chin(landmarks, face_height),
        "skin": _measure_skin(rgb_array, landmarks),
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
    return MeasurementResult(
        True,
        metrics={
            "left_height_ratio": round(left_height, 4),
            "right_height_ratio": round(right_height, 4),
            "symmetry_delta": round(abs(left_height - right_height), 4),
        },
    )


def _measure_eyes(landmarks: list[Any], scale: float) -> MeasurementResult:
    left_width = _distance(landmarks, _LEFT_EYE_OUTER, _LEFT_EYE_INNER) / scale
    right_width = _distance(landmarks, _RIGHT_EYE_INNER, _RIGHT_EYE_OUTER) / scale
    left_openness = _distance(landmarks, _LEFT_EYE_TOP, _LEFT_EYE_BOTTOM) / scale
    right_openness = _distance(landmarks, _RIGHT_EYE_TOP, _RIGHT_EYE_BOTTOM) / scale
    return MeasurementResult(
        True,
        metrics={
            "left_width_ratio": round(left_width, 4),
            "right_width_ratio": round(right_width, 4),
            "left_openness_ratio": round(left_openness, 4),
            "right_openness_ratio": round(right_openness, 4),
            "symmetry_delta": round(abs(left_width - right_width), 4),
        },
    )


def _measure_nose(landmarks: list[Any], scale: float) -> MeasurementResult:
    width = _distance(landmarks, _NOSE_LEFT_ALA, _NOSE_RIGHT_ALA) / scale
    length = _distance(landmarks, _NOSE_BRIDGE, _NOSE_BASE) / scale
    return MeasurementResult(
        True,
        metrics={
            "width_ratio": round(width, 4),
            "length_ratio": round(length, 4),
            "width_to_length_ratio": round(width / length, 4) if length else 0.0,
        },
    )


def _measure_cheeks(landmarks: list[Any], face_width: float) -> MeasurementResult:
    width = _distance(landmarks, _CHEEK_LEFT, _CHEEK_RIGHT) / face_width if face_width else 0.0
    return MeasurementResult(True, metrics={"width_to_face_ratio": round(width, 4)})


def _measure_jaw(landmarks: list[Any], face_width: float) -> MeasurementResult:
    width = _distance(landmarks, _JAW_LEFT, _JAW_RIGHT) / face_width if face_width else 0.0
    return MeasurementResult(True, metrics={"width_to_face_ratio": round(width, 4)})


def _measure_lips(landmarks: list[Any], scale: float) -> MeasurementResult:
    width = _distance(landmarks, _MOUTH_LEFT, _MOUTH_RIGHT) / scale
    fullness = _distance(landmarks, _LIP_UPPER_TOP, _LIP_LOWER_BOTTOM) / scale
    return MeasurementResult(
        True,
        metrics={
            "width_ratio": round(width, 4),
            "fullness_ratio": round(fullness, 4),
        },
    )


def _measure_chin(landmarks: list[Any], face_height: float) -> MeasurementResult:
    projection = (
        _distance(landmarks, _LIP_LOWER_BOTTOM, _CHIN) / face_height if face_height else 0.0
    )
    return MeasurementResult(True, metrics={"projection_to_face_ratio": round(projection, 4)})


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
