"""User profile endpoint (FR-017) -- see docs/api-specification.md §3.
Deliberately thin, same posture as auth.get_me: no service module needed
since this is a pure read of the already-loaded current_user.
"""

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.users import UserProfileOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserProfileOut)
async def get_my_profile(user: User = Depends(get_current_user)) -> UserProfileOut:
    """Aliases /auth/me with created_at added, for the dashboard's profile
    card -- see UserProfileOut's docstring for why there is no PATCH here."""
    return UserProfileOut.model_validate(user)
