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


class PhotoSetStatusResponse(BaseModel):
    angles: list[PhotoAngleStatus]
    completed: bool
