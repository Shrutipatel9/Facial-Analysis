import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

AnalysisStatus = Literal["none", "processing", "completed", "failed"]


class TriggerAnalysisResponse(BaseModel):
    id: uuid.UUID
    status: Literal["processing"]


class AnalysisStatusResponse(BaseModel):
    status: AnalysisStatus
    analysis_id: uuid.UUID | None = None


class AnalysisOut(BaseModel):
    id: uuid.UUID
    status: Literal["processing", "completed", "failed"]
    measurements: dict[str, Any]
    narrative_result: dict[str, Any] | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}
