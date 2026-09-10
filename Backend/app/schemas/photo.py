import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

CaptureMethod = Literal["upload", "camera"]
ValidationStatus = Literal["passed", "failed"]


class CheckResultOut(BaseModel):
    check: str
    passed: bool
    reason: str | None = None


class PhotoOut(BaseModel):
    id: uuid.UUID
    angle: str
    capture_method: CaptureMethod
    validation_status: ValidationStatus
    checks: list[CheckResultOut]
    uploaded_at: datetime


class PhotoAngleStatus(BaseModel):
    angle: str
    label: str
    instruction: str
    photo: PhotoOut | None = None


class IdentityCheckOut(BaseModel):
    """Cross-photo "is this the same person in all three angles" result --
    see photo_validation_service.check_photo_set_identity. Only meaningful
    (non-None on the response) once every required angle already has a
    passed photo; there's nothing to compare before then."""

    consistent: bool
    mismatched_angles: list[str] = []
    message: str | None = None


class PhotoSetStatusResponse(BaseModel):
    angles: list[PhotoAngleStatus]
    completed: bool
    identity_check: IdentityCheckOut | None = None
