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
)

MIN_SHORTEST_SIDE_PX = 640
BRIGHTNESS_MIN = 60.0
BRIGHTNESS_MAX = 200.0
FRAME_PROPORTION_MIN = 0.15
FRAME_PROPORTION_MAX = 0.80
FACE_DETECTION_MIN_CONFIDENCE = 0.5
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


def validate_photo(content: bytes) -> list[CheckResult]:
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
        ]

    rgb_image = image.convert("RGB")
    results = [CheckResult("file_readable", True)]
    results.append(_check_resolution(rgb_image))
    results.append(_check_brightness(rgb_image))

    detection_result = _detect_faces(rgb_image)
    face_count_result, single_detection = _check_face_count(detection_result)
    results.append(face_count_result)

    if single_detection is None:
        results.append(CheckResult("frame_proportion", False, _SKIPPED_NO_SINGLE_FACE))
        results.append(CheckResult("occlusion", False, _SKIPPED_NO_SINGLE_FACE))
    else:
        results.append(_check_frame_proportion(single_detection, rgb_image.size))
        results.append(_check_occlusion(single_detection))

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


def _detect_faces(image: Image.Image) -> FaceDetectorResult:
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
