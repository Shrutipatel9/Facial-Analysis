import uuid
from typing import Any, Literal

from pydantic import BaseModel

# Same "plain Literal, not an Enum class" convention as schemas/photo.py's
# CaptureMethod/ValidationStatus -- FastAPI validates a Literal path param
# automatically (422 on an unknown value) with no extra Enum boilerplate.
AiVisualKind = Literal["hairstyle", "outfit", "aging", "potential"]


class AiVisualOut(BaseModel):
    id: uuid.UUID
    kind: str
    variation_index: int
    # "pending" | "generating" | "generated" | "failed"
    status: str
    name: str | None = None
    is_recommended: bool = False
    attributes: dict[str, Any] | None = None
    explanation: str | None = None
    error_reason: str | None = None
