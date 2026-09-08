"""Photo upload endpoints -- thin: all logic lives in
app/services/photo_service.py. See docs/photo_capture_spec.md for the
full angle/flow spec.
"""

import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.photo import Photo
from app.models.user import User
from app.schemas.photo import CheckResultOut, PhotoAngleStatus, PhotoOut, PhotoSetStatusResponse
from app.services import photo_service
from app.services.photo_validation_service import REQUIRED_ANGLES

router = APIRouter(prefix="/photos", tags=["photos"])


def _photo_out(photo: Photo) -> PhotoOut:
    checks = photo.validation_result.get("checks", [])
    return PhotoOut(
        id=photo.id,
        angle=photo.angle,
        capture_method=photo.capture_method,  # type: ignore[arg-type]
        validation_status=photo.validation_status,  # type: ignore[arg-type]
        checks=[CheckResultOut(**check) for check in checks],
        uploaded_at=photo.uploaded_at,
    )


# 200, not 201 -- a request can be either a first upload for this angle or
# a replace, and either way a successful *request* can still report a
# failed validation outcome (BR-005) rather than an HTTP error. See
# photo_service.upload_photo.
@router.post("", response_model=PhotoOut)
async def upload_photo(
    angle: str = Form(...),
    capture_method: str = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PhotoOut:
    content = await file.read()
    photo = await photo_service.upload_photo(
        db,
        user.id,
        angle=angle,
        capture_method=capture_method,
        content=content,
        content_type=file.content_type,
    )
    return _photo_out(photo)


@router.get("/status", response_model=PhotoSetStatusResponse)
async def get_photos_status(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> PhotoSetStatusResponse:
    status_by_angle = await photo_service.get_status_by_angle(db, user.id)
    angles = []
    for angle in REQUIRED_ANGLES:
        photo = status_by_angle[angle.id]
        angles.append(
            PhotoAngleStatus(
                angle=angle.id,
                label=angle.label,
                instruction=angle.instruction,
                photo=_photo_out(photo) if photo is not None else None,
            )
        )
    completed = await photo_service.is_photo_set_ready(db, user.id)
    return PhotoSetStatusResponse(angles=angles, completed=completed)


@router.get("/{photo_id}", response_model=PhotoOut)
async def get_photo(
    photo_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PhotoOut:
    photo = await photo_service.get_photo(db, user.id, photo_id)
    return _photo_out(photo)
