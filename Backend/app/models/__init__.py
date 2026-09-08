"""SQLAlchemy models.

Every model module added here must be imported below so Alembic's
autogenerate (see alembic/env.py) can discover it via Base.metadata.
"""

# Imported for their side effect of registering model classes on Base.metadata.
from app.models.otp_record import OTPRecord
from app.models.photo import Photo
from app.models.questionnaire_response import QuestionnaireResponse
from app.models.refresh_token import RefreshToken
from app.models.user import User

__all__ = ["User", "OTPRecord", "RefreshToken", "QuestionnaireResponse", "Photo"]
