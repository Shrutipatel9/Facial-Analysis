"""Photo validation checks (BR-005, ASM-002) -- pure functions, no DB or
storage dependency, so they're independently unit-testable with raw bytes
and fixture images alone (see tests/integration/test_photo_flow.py).

Six checks always run and are always all six reported in the result (not
just failures) so the frontend can render a full pass/fail checklist
against photo_capture_spec.md §3's per-photo guidance. A photo that fails
one or more checks is not an HTTP error -- see photo_service.upload_photo.

Thresholds below are delivery-team decisions (docs/security.md §7) --
ASM-002 left the exact numbers undecided in the requirements doc; expect a
tuning pass once real device photos go through Phase 4/5 integration.
"""

import io
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import pillow_heif
from mediapipe import Image as MPImage
from mediapipe import ImageFormat
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import FaceDetector, FaceDetectorOptions
from mediapipe.tasks.python.vision.face_detector import FaceDetectorResult
from PIL import Image, UnidentifiedImageError

from app.services.face_identity_service import (
    IDENTITY_COSINE_DISTANCE_THRESHOLD as IDENTITY_MISMATCH_THRESHOLD,
)
from app.services.face_identity_service import (
    IdentityCheckResult,
    check_photo_set_identity as _check_photo_set_identity_impl,
)

pillow_heif.register_heif_opener()

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_FACE_MODEL_PATH = _BASE_DIR / "var" / "models" / "blaze_face_short_range.tflite"

CHECK_NAMES: tuple[str, ...] = (
    "file_readable",
    "resolution",
    "brightness",
    "face_count",
    "frame_proportion",
    "occlusion",
    "pose_match",
)

MIN_SHORTEST_SIDE_PX = 640
BRIGHTNESS_MIN = 60.0
BRIGHTNESS_MAX = 200.0
FRAME_PROPORTION_MIN = 0.15
FRAME_PROPORTION_MAX = 0.80
FACE_DETECTION_MIN_CONFIDENCE = 0.5
# |nose x-offset from the eye-midpoint, normalized by eye span| below this
# reads as a frontal pose; at or above it reads as a 3/4 turn (direction
# from the offset's sign). First-pass heuristic (ASM-002 posture, like
# every other threshold in this module) calibrated against this project's
# own real frontal fixture (~0.05) and synthetic turned fixtures (~0.17,
# ~0.24) -- see tests/fixtures/photos/pass_{right,left}_3q.jpg and
# docs/security.md §6. Expect a tuning pass once real device photos of
# genuine 3/4 turns go through this.
POSE_YAW_FRONTAL_THRESHOLD = 0.12
# Stricter than FACE_DETECTION_MIN_CONFIDENCE above. NormalizedKeypoint.score
# and .label are always 0.0 / None for the BlazeFace short-range model
# (verified empirically against a real portrait, not documented anywhere in
# MediaPipe's own docs) -- per-feature (eyes/mouth) confidence isn't
# available, so occlusion falls back to the overall detection confidence at
# a higher floor. This is a simplified heuristic, not a real glasses/hat
# classifier -- see docs/photo_capture_spec.md's occlusion note.
OCCLUSION_CONFIDENCE_FLOOR = 0.75

_SKIPPED_UNREADABLE = "Skipped: file could not be read."
_SKIPPED_NO_SINGLE_FACE = "Skipped: exactly one face is required for this check."
_SKIPPED_UNKNOWN_ANGLE = "Skipped: unknown angle."


@dataclass(frozen=True)
class PhotoAngle:
    id: str
    label: str
    instruction: str


# ASM-004 [Assumption, pending client confirmation --
# docs/photo_capture_spec.md §5]: 3-angle default, not Qoves' full 7-pose
# set. Kept as a small, swappable constant per the spec's own
# implementation constraint (§1) so a future 3->7 change is a constant
# edit, not a rearchitecture.
REQUIRED_ANGLES: tuple[PhotoAngle, ...] = (
    PhotoAngle(
        "front",
        "Front Face",
        "Entire face head-on with a neutral expression.",
    ),
    PhotoAngle(
        "right_3q",
        "Right Side",
        "Turn your head to show your right side at roughly a 45° angle.",
    ),
    PhotoAngle(
        "left_3q",
        "Left Side",
        "Turn your head to show your left side at roughly a 45° angle.",
    ),
)

REQUIRED_ANGLES_BY_ID: dict[str, PhotoAngle] = {angle.id: angle for angle in REQUIRED_ANGLES}


@dataclass(frozen=True)
class CheckResult:
    check: str
    passed: bool
    reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {"check": self.check, "passed": self.passed, "reason": self.reason}


@lru_cache
def _get_face_detector() -> FaceDetector:
    base_options = BaseOptions(model_asset_path=str(_FACE_MODEL_PATH))
    options = FaceDetectorOptions(
        base_options=base_options, min_detection_confidence=FACE_DETECTION_MIN_CONFIDENCE
    )
    return FaceDetector.create_from_options(options)


def validate_photo(content: bytes, angle_id: str) -> list[CheckResult]:
    try:
        image = Image.open(io.BytesIO(content))
        image.load()
    except (UnidentifiedImageError, OSError):
        return [
            CheckResult("file_readable", False, "The file could not be read as an image."),
            CheckResult("resolution", False, _SKIPPED_UNREADABLE),
            CheckResult("brightness", False, _SKIPPED_UNREADABLE),
            CheckResult("face_count", False, _SKIPPED_UNREADABLE),
            CheckResult("frame_proportion", False, _SKIPPED_UNREADABLE),
            CheckResult("occlusion", False, _SKIPPED_UNREADABLE),
            CheckResult("pose_match", False, _SKIPPED_UNREADABLE),
        ]

    rgb_image = image.convert("RGB")
    results = [CheckResult("file_readable", True)]
    results.append(_check_resolution(rgb_image))
    results.append(_check_brightness(rgb_image))

    detection_result = detect_faces(rgb_image)
    face_count_result, single_detection = _check_face_count(detection_result)
    results.append(face_count_result)

    if single_detection is None:
        results.append(CheckResult("frame_proportion", False, _SKIPPED_NO_SINGLE_FACE))
        results.append(CheckResult("occlusion", False, _SKIPPED_NO_SINGLE_FACE))
        results.append(CheckResult("pose_match", False, _SKIPPED_NO_SINGLE_FACE))
    else:
        results.append(_check_frame_proportion(single_detection, rgb_image.size))
        results.append(_check_occlusion(single_detection))
        results.append(_check_pose_match(single_detection, angle_id))

    return results


def _check_resolution(image: Image.Image) -> CheckResult:
    shortest_side = min(image.size)
    if shortest_side < MIN_SHORTEST_SIDE_PX:
        return CheckResult(
            "resolution",
            False,
            f"Image is too small ({shortest_side}px shortest side; minimum {MIN_SHORTEST_SIDE_PX}px).",
        )
    return CheckResult("resolution", True)


def _check_brightness(image: Image.Image) -> CheckResult:
    grayscale = np.asarray(image.convert("L"), dtype=np.float64)
    mean_brightness = float(grayscale.mean())
    if mean_brightness < BRIGHTNESS_MIN:
        return CheckResult("brightness", False, "Photo is too dark. Use even, brighter lighting.")
    if mean_brightness > BRIGHTNESS_MAX:
        return CheckResult(
            "brightness", False, "Photo is too bright or overexposed. Reduce lighting or glare."
        )
    return CheckResult("brightness", True)


def detect_faces(image: Image.Image) -> FaceDetectorResult:
    """Public -- also reused by facial_measurement_service.py's ear
    measurement (the BlazeFace keypoints include ear-tragion points, and
    there's no reason to load a second lightweight detector instance)."""
    mp_image = MPImage(image_format=ImageFormat.SRGB, data=np.asarray(image, dtype=np.uint8))
    return _get_face_detector().detect(mp_image)


def _check_face_count(detection_result: FaceDetectorResult) -> tuple[CheckResult, object | None]:
    detections = detection_result.detections
    count = len(detections)
    if count == 0:
        return CheckResult("face_count", False, "No face detected in the photo."), None
    if count > 1:
        return CheckResult("face_count", False, "More than one face detected in the photo."), None
    return CheckResult("face_count", True), detections[0]


def _check_frame_proportion(detection: object, image_size: tuple[int, int]) -> CheckResult:
    width, height = image_size
    bbox = detection.bounding_box  # type: ignore[attr-defined]
    proportion = (bbox.width * bbox.height) / (width * height)
    if proportion < FRAME_PROPORTION_MIN:
        return CheckResult(
            "frame_proportion", False, "Face is too small in the frame. Move closer to the camera."
        )
    if proportion > FRAME_PROPORTION_MAX:
        return CheckResult(
            "frame_proportion", False, "Face is too close to the camera. Move back a little."
        )
    return CheckResult("frame_proportion", True)


def _check_occlusion(detection: object) -> CheckResult:
    categories = detection.categories  # type: ignore[attr-defined]
    confidence = categories[0].score if categories else 0.0
    if confidence < OCCLUSION_CONFIDENCE_FLOOR:
        return CheckResult(
            "occlusion",
            False,
            "Face may be partially obstructed. Remove hats, glasses, or hair covering the face.",
        )
    return CheckResult("occlusion", True)


def estimate_yaw_ratio(detection: object) -> float:
    """Normalized horizontal offset of the nose tip from the eye midpoint,
    scaled by eye span -- ~0 for a frontal pose, meaningfully positive or
    negative for a 3/4 turn. Uses BlazeFace's 6 keypoints (indices 0/1 are
    the subject's own right/left eye -- MediaPipe's documented convention,
    verified empirically against this project's own model and the real/
    synthetic fixtures in tests/fixtures/photos/). Public so it's directly
    unit-testable against hand-built keypoint fixtures, not just real
    images."""
    right_eye, left_eye, nose = detection.keypoints[0], detection.keypoints[1], detection.keypoints[2]  # type: ignore[attr-defined]
    eye_mid_x = (right_eye.x + left_eye.x) / 2
    eye_span = abs(left_eye.x - right_eye.x) or 1e-6
    return (nose.x - eye_mid_x) / eye_span


def classify_pose(detection: object) -> str:
    """Returns "front", "right_3q", or "left_3q" -- see
    estimate_yaw_ratio's docstring. A positive ratio means the nose sits
    toward the subject's own left eye (image-right), i.e. the subject's
    left side has foreshortened/turned away and their right side is more
    prominent to the camera -- "right_3q"; negative is the mirror case."""
    ratio = estimate_yaw_ratio(detection)
    if abs(ratio) < POSE_YAW_FRONTAL_THRESHOLD:
        return "front"
    return "right_3q" if ratio > 0 else "left_3q"


def _check_pose_match(detection: object, angle_id: str) -> CheckResult:
    if angle_id not in REQUIRED_ANGLES_BY_ID:
        return CheckResult("pose_match", False, _SKIPPED_UNKNOWN_ANGLE)
    detected = classify_pose(detection)
    if detected == angle_id:
        return CheckResult("pose_match", True)
    expected_label = REQUIRED_ANGLES_BY_ID[angle_id].label
    return CheckResult(
        "pose_match",
        False,
        f"This doesn't look like a {expected_label.lower()} photo. Upload a photo matching this specific angle.",
    )


# --- Cross-photo identity (set-level, once all angles passed) ---------------
# ArcFace embeddings live in face_identity_service.py. Re-exported names
# (IDENTITY_MISMATCH_THRESHOLD, IdentityCheckResult) keep existing imports working.


def check_photo_set_identity(photos: dict[str, bytes]) -> IdentityCheckResult:
    """Delegates to ArcFace embedding comparison -- see face_identity_service."""
    labels = {angle_id: angle.label.lower() for angle_id, angle in REQUIRED_ANGLES_BY_ID.items()}
    return _check_photo_set_identity_impl(photos, angle_labels=labels)
