"""SQLAlchemy models.

Every model module added here must be imported below so Alembic's
autogenerate (see alembic/env.py) can discover it via Base.metadata.
"""

# Imported for their side effect of registering model classes on Base.metadata.
from app.models.facial_analysis_result import FacialAnalysisResult
from app.models.otp_record import OTPRecord
from app.models.payment import Payment
from app.models.photo import Photo
from app.models.photo_blob import PhotoBlob
from app.models.questionnaire_response import QuestionnaireResponse
from app.models.refresh_token import RefreshToken
from app.models.report import Report
from app.models.report_feature_image import ReportFeatureImage
from app.models.report_pdf_blob import ReportPdfBlob
from app.models.user import User

__all__ = [
    "User",
    "OTPRecord",
    "RefreshToken",
    "QuestionnaireResponse",
    "Photo",
    "PhotoBlob",
    "FacialAnalysisResult",
    "Report",
    "ReportPdfBlob",
    "ReportFeatureImage",
    "Payment",
]
