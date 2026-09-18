"""FR-027 (Milestone 3) -- Care Team support request schemas."""

import uuid

from pydantic import BaseModel, Field


class SupportRequestCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=5000)
    # Auto-attached client-side from the current report in view, never a
    # user-entered field -- see SupportSection.tsx.
    report_id: uuid.UUID | None = None
