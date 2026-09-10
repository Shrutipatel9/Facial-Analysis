"""Cross-photo identity check via ArcFace face embeddings (onnxruntime).

Replaces the previous MediaPipe landmark-ratio "signature", which was too
pose-sensitive: the same person on left_3q vs right_3q often looked like a
mismatch, and the old matcher then *always* kept `front` and flagged the
other two -- which is exactly the static-front bug users hit.

This module:
  1. Detects/aligns the face with MediaPipe FaceLandmarker (5-point ArcFace
     alignment into 112x112).
  2. Runs a local ArcFace R50 ONNX model (buffalo_l recognition weights) to
     get a 512-d L2-normalized embedding.
  3. Compares pairs with cosine distance.
  4. Names mismatched angle(s) by match-count vote with **no preferred
     angle** -- whichever photo(s) match the fewest others are flagged.

Model file: `Backend/var/models/w600k_r50.onnx` (auto-downloaded on first use).
"""

from __future__ import annotations

import io
import logging
from functools import lru_cache
from pathlib import Path
from typing import TypedDict

import cv2
import httpx
import numpy as np
import onnxruntime as ort
from mediapipe import Image as MPImage
from mediapipe import ImageFormat
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import FaceLandmarker, FaceLandmarkerOptions, RunningMode
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_LANDMARKER_MODEL_PATH = _BASE_DIR / "var" / "models" / "face_landmarker.task"
_ARCFACE_MODEL_PATH = _BASE_DIR / "var" / "models" / "w600k_r50.onnx"
# Official InsightFace buffalo_l recognition weights (ArcFace R50).
_ARCFACE_MODEL_URL = (
    "https://huggingface.co/public-data/insightface/resolve/main/models/buffalo_l/w600k_r50.onnx"
)

# Cosine distance = 1 - cos_sim on L2-normalized embeddings.
# ArcFace same-identity pairs are typically well below ~0.35-0.40 even across
# moderate pose change; different identities sit much higher. 0.45 leaves
# margin for 3/4 views without the old ratio-signature false rejects.
IDENTITY_COSINE_DISTANCE_THRESHOLD = 0.45

# MediaPipe FaceLandmarker indices approximating the 5 ArcFace align points
# (left eye, right eye, nose tip, left mouth, right mouth).
_ALIGN_LEFT_EYE = 33
_ALIGN_RIGHT_EYE = 263
_ALIGN_NOSE = 1
_ALIGN_MOUTH_LEFT = 61
_ALIGN_MOUTH_RIGHT = 291

# Standard ArcFace 112x112 reference landmarks.
_ARCFACE_DST = np.array(
    [
        [38.2946, 51.6963],
        [73.5318, 51.5014],
        [56.0252, 71.7366],
        [41.5493, 92.3655],
        [70.7299, 92.2041],
    ],
    dtype=np.float32,
)


class IdentityCheckResult(TypedDict):
    consistent: bool
    mismatched_angles: list[str]
    message: str | None


def _ensure_arcface_model() -> Path:
    if _ARCFACE_MODEL_PATH.is_file():
        return _ARCFACE_MODEL_PATH
    _ARCFACE_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading ArcFace model to %s …", _ARCFACE_MODEL_PATH)
    with httpx.stream("GET", _ARCFACE_MODEL_URL, follow_redirects=True, timeout=120.0) as response:
        response.raise_for_status()
        tmp_path = _ARCFACE_MODEL_PATH.with_suffix(".onnx.partial")
        with tmp_path.open("wb") as out:
            for chunk in response.iter_bytes():
                out.write(chunk)
        tmp_path.replace(_ARCFACE_MODEL_PATH)
    return _ARCFACE_MODEL_PATH


@lru_cache
def _get_landmarker() -> FaceLandmarker:
    options = FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(_LANDMARKER_MODEL_PATH)),
        running_mode=RunningMode.IMAGE,
        num_faces=1,
    )
    return FaceLandmarker.create_from_options(options)


@lru_cache
def _get_arcface_session() -> ort.InferenceSession:
    model_path = _ensure_arcface_model()
    return ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])


def _align_face(rgb: np.ndarray, landmarks_xy: np.ndarray) -> np.ndarray:
    """Similarity-transform crop to ArcFace's 112x112 template."""
    transform, _ = cv2.estimateAffinePartial2D(landmarks_xy, _ARCFACE_DST, method=cv2.LMEDS)
    if transform is None:
        # Fallback: tight square crop around landmark centroid.
        center = landmarks_xy.mean(axis=0)
        scale = max(np.linalg.norm(landmarks_xy[0] - landmarks_xy[1]) * 2.2, 64.0)
        half = scale / 2
        x1, y1 = int(center[0] - half), int(center[1] - half)
        x2, y2 = int(center[0] + half), int(center[1] + half)
        h, w = rgb.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        crop = rgb[y1:y2, x1:x2]
        return cv2.resize(crop, (112, 112), interpolation=cv2.INTER_LINEAR)
    return cv2.warpAffine(rgb, transform, (112, 112), borderValue=0.0)


def compute_face_embedding(content: bytes) -> np.ndarray | None:
    """512-d L2-normalized ArcFace embedding, or None if no usable face."""
    try:
        image = Image.open(io.BytesIO(content)).convert("RGB")
    except (UnidentifiedImageError, OSError):
        return None

    rgb = np.asarray(image, dtype=np.uint8)
    mp_image = MPImage(image_format=ImageFormat.SRGB, data=rgb)
    result = _get_landmarker().detect(mp_image)
    if not result.face_landmarks:
        return None

    landmarks = result.face_landmarks[0]
    pts = np.array(
        [
            [landmarks[_ALIGN_LEFT_EYE].x * rgb.shape[1], landmarks[_ALIGN_LEFT_EYE].y * rgb.shape[0]],
            [landmarks[_ALIGN_RIGHT_EYE].x * rgb.shape[1], landmarks[_ALIGN_RIGHT_EYE].y * rgb.shape[0]],
            [landmarks[_ALIGN_NOSE].x * rgb.shape[1], landmarks[_ALIGN_NOSE].y * rgb.shape[0]],
            [landmarks[_ALIGN_MOUTH_LEFT].x * rgb.shape[1], landmarks[_ALIGN_MOUTH_LEFT].y * rgb.shape[0]],
            [landmarks[_ALIGN_MOUTH_RIGHT].x * rgb.shape[1], landmarks[_ALIGN_MOUTH_RIGHT].y * rgb.shape[0]],
        ],
        dtype=np.float32,
    )
    aligned = _align_face(rgb, pts)

    # ArcFace training convention: BGR, (x - 127.5) / 127.5, NCHW float32.
    blob = cv2.cvtColor(aligned, cv2.COLOR_RGB2BGR).astype(np.float32)
    blob = (blob - 127.5) / 127.5
    blob = np.transpose(blob, (2, 0, 1))[None, ...]

    session = _get_arcface_session()
    input_name = session.get_inputs()[0].name
    embedding = session.run(None, {input_name: blob})[0][0].astype(np.float64)
    norm = np.linalg.norm(embedding)
    if norm < 1e-8:
        return None
    return embedding / norm


def embedding_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine distance on already L2-normalized embeddings."""
    return float(1.0 - np.dot(a, b))


def determine_mismatched_angles(
    angles: list[str],
    pairwise: dict[tuple[str, str], float],
    *,
    threshold: float = IDENTITY_COSINE_DISTANCE_THRESHOLD,
) -> list[str]:
    """Flag every angle with the lowest pairwise *match count*.

    No preferred/reference angle (front is not special). Examples:
      - one odd photo → that photo only (match count 0)
      - all three different people → all three (everyone has count 0)
      - two match, one does not → the one
    """

    def distance_between(a: str, b: str) -> float:
        return pairwise[(a, b)] if (a, b) in pairwise else pairwise[(b, a)]

    counts = {angle: 0 for angle in angles}
    for (a, b), distance in pairwise.items():
        if distance <= threshold:
            counts[a] += 1
            counts[b] += 1

    min_count = min(counts.values())
    lowest = [angle for angle in angles if counts[angle] == min_count]
    if len(lowest) == 1 or min_count == 0:
        # Unique odd-one-out, or every unmatched photo (incl. all-different).
        return lowest

    # Tie at count >= 1 (rare hub case with good embeddings): name the single
    # tied angle farthest from the best-connected photo -- still no front bias.
    hub = max(angles, key=lambda angle: (counts[angle], angle))
    return [max(lowest, key=lambda angle: distance_between(hub, angle))]


def _format_identity_mismatch_message(mismatched_angles: list[str], labels: dict[str, str]) -> str:
    named = [labels.get(angle, angle) for angle in mismatched_angles]
    if len(named) == 1:
        subject = f"The {named[0]} photo doesn't"
    elif len(named) == len(labels):
        subject = "These photos don't"
    else:
        subject = f"Your {' and '.join(named)} photos don't"
    return (
        f"{subject} appear to match the person in your other photos. "
        "Please make sure all three photos are of the same person, then re-upload the flagged photo(s)."
    )


def check_photo_set_identity(
    photos: dict[str, bytes],
    *,
    angle_labels: dict[str, str] | None = None,
) -> IdentityCheckResult:
    """Compare embeddings for every angle → bytes mapping.

    Callers should pass only already-passed photos. Returns consistent=True
    when fewer than 3 embeddings can be computed (nothing meaningful to
    vote on) or when every pairwise distance is within threshold.
    """
    embeddings: dict[str, np.ndarray] = {}
    for angle, content in photos.items():
        embedding = compute_face_embedding(content)
        if embedding is not None:
            embeddings[angle] = embedding

    if len(embeddings) < 3:
        return {"consistent": True, "mismatched_angles": [], "message": None}

    angles = list(embeddings.keys())
    pairwise: dict[tuple[str, str], float] = {}
    for i, a in enumerate(angles):
        for b in angles[i + 1 :]:
            pairwise[(a, b)] = embedding_distance(embeddings[a], embeddings[b])

    if all(distance <= IDENTITY_COSINE_DISTANCE_THRESHOLD for distance in pairwise.values()):
        return {"consistent": True, "mismatched_angles": [], "message": None}

    mismatched = determine_mismatched_angles(angles, pairwise)
    labels = angle_labels or {angle: angle.replace("_", " ") for angle in mismatched}
    return {
        "consistent": False,
        "mismatched_angles": mismatched,
        "message": _format_identity_mismatch_message(mismatched, labels),
    }
