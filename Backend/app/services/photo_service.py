"""Photo upload orchestration: validation + storage + DB upsert-by-angle
(BR-004, BR-005). Thin compared to photo_validation_service.py -- that
module is pure/independently-testable; this one wires it to the DB and
PhotoStorage.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.cv_executor import run_cv_task
from app.exceptions import (
    PhotoAngleUnknownError,
    PhotoNotFoundError,
    PhotoSetAlreadyCompleteError,
    PhotoUploadInvalidError,
)
from app.models.payment import Payment
from app.models.photo import Photo
from app.services.photo_storage import get_photo_storage
from app.services.photo_validation_service import (
    REQUIRED_ANGLES_BY_ID,
    IdentityCheckResult,
    check_photo_set_identity,
    validate_photo,
)

# Pillow (+ pillow-heif) decodes all of these; DNG/RAW is intentionally not
# supported this pass -- real RAW decoding needs rawpy/libraw, a much
# heavier dependency than the web-upload flow's realistic needs justify
# right now. Flagged as an explicit follow-up, not silently dropped --
# see D:\zzz\photo-upload-validation\plans.md's Open Questions.
_ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/heic": ".heic",
    "image/heif": ".heic",
}


async def upload_photo(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    angle: str,
    capture_method: str,
    content: bytes,
    content_type: str | None,
) -> Photo:
    if angle not in REQUIRED_ANGLES_BY_ID:
        raise PhotoAngleUnknownError()

    if capture_method not in ("upload", "camera"):
        raise PhotoUploadInvalidError("capture_method must be 'upload' or 'camera'.")

    if not content:
        raise PhotoUploadInvalidError("No file was uploaded.")

    settings = get_settings()
    if len(content) > settings.photo_max_upload_bytes:
        raise PhotoUploadInvalidError("File is too large.")

    extension = _ALLOWED_CONTENT_TYPES.get((content_type or "").lower())
    if extension is None:
        raise PhotoUploadInvalidError("Unsupported file type. Upload a JPEG, PNG, or HEIC photo.")

    # Lock the set once payment has succeeded (analysis consumes these
    # photos). Until then, users may replace any angle from the review
    # screen — including after all three have already passed.
    if await _has_succeeded_payment(db, user_id):
        raise PhotoSetAlreadyCompleteError()

    checks = await run_cv_task(validate_photo, content, angle)
    validation_status = "passed" if all(check.passed for check in checks) else "failed"

    storage = get_photo_storage()
    storage_reference = await storage.save(
        user_id=user_id, angle=angle, content=content, extension=extension
    )

    existing = await _get_by_angle(db, user_id, angle)
    if existing is not None:
        old_reference = existing.storage_reference
        existing.capture_method = capture_method
        existing.storage_reference = storage_reference
        existing.validation_status = validation_status
        existing.validation_result = {"checks": [check.to_dict() for check in checks]}
        record = existing
        if old_reference != storage_reference:
            await storage.delete(old_reference)
    else:
        record = Photo(
            user_id=user_id,
            angle=angle,
            capture_method=capture_method,
            storage_reference=storage_reference,
            validation_status=validation_status,
            validation_result={"checks": [check.to_dict() for check in checks]},
        )
        db.add(record)

    await db.flush()
    await db.refresh(record)
    return record


async def _get_by_angle(db: AsyncSession, user_id: uuid.UUID, angle: str) -> Photo | None:
    result = await db.execute(select(Photo).where(Photo.user_id == user_id, Photo.angle == angle))
    return result.scalar_one_or_none()


async def _has_succeeded_payment(db: AsyncSession, user_id: uuid.UUID) -> bool:
    # Queried here directly to avoid a payment_service ↔ photo_service import cycle.
    result = await db.execute(
        select(Payment.id)
        .where(Payment.user_id == user_id, Payment.status == "succeeded")
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def get_photo(db: AsyncSession, user_id: uuid.UUID, photo_id: uuid.UUID) -> Photo:
    result = await db.execute(select(Photo).where(Photo.id == photo_id, Photo.user_id == user_id))
    photo = result.scalar_one_or_none()
    if photo is None:
        raise PhotoNotFoundError()
    return photo


async def get_status_by_angle(db: AsyncSession, user_id: uuid.UUID) -> dict[str, Photo | None]:
    """REQUIRED_ANGLES-ordered angle_id -> Photo|None (None if that angle
    has no upload yet)."""
    result = await db.execute(select(Photo).where(Photo.user_id == user_id))
    by_angle = {photo.angle: photo for photo in result.scalars().all()}
    return {angle_id: by_angle.get(angle_id) for angle_id in REQUIRED_ANGLES_BY_ID}


async def is_photo_set_ready(db: AsyncSession, user_id: uuid.UUID) -> bool:
    """The single BR-004 enforcement point -- every required angle has a
    passed photo. Phase 4's eventual analysis-trigger endpoint must call
    this same function as its first guard clause; do not re-derive this
    condition anywhere else."""
    status_by_angle = await get_status_by_angle(db, user_id)
    return all(
        photo is not None and photo.validation_status == "passed" for photo in status_by_angle.values()
    )


async def get_identity_check(db: AsyncSession, user_id: uuid.UUID) -> IdentityCheckResult | None:
    """Cross-photo "same person in all three angles" check -- returns None
    until the set is actually complete (is_photo_set_ready), since there's
    nothing meaningful to compare before then. Loads every angle's actual
    stored bytes (not just their DB rows) because
    photo_validation_service.check_photo_set_identity needs to re-run
    MediaPipe landmark detection on each one -- raw landmarks are never
    persisted, only the pass/fail check results are (see Photo.
    validation_result), same posture as facial_measurement_service's own
    "re-detect from stored bytes, don't persist landmarks" convention."""
    if not await is_photo_set_ready(db, user_id):
        return None

    status_by_angle = await get_status_by_angle(db, user_id)
    storage = get_photo_storage()
    photos: dict[str, bytes] = {}
    for angle_id, photo in status_by_angle.items():
        assert photo is not None  # guaranteed by is_photo_set_ready above
        photos[angle_id] = await storage.load(photo.storage_reference)

    return await run_cv_task(check_photo_set_identity, photos)
