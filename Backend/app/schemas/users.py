import uuid
from datetime import datetime

from pydantic import BaseModel


class UserProfileOut(BaseModel):
    """Dashboard-facing user profile -- see docs/api-specification.md §3.
    A superset of auth.UserOut (adds created_at for "member since"). Not
    independently editable here -- full_name is captured once at signup
    (RegisterRequest.full_name) and password changes go through
    POST /auth/change-password, not this endpoint (see
    docs/client_requirements.md's ASM-009 for the profile-scope history)."""

    id: uuid.UUID
    email: str
    full_name: str | None
    role: str
    verification_status: str
    created_at: datetime

    model_config = {"from_attributes": True}
