"""Maps domain exceptions (app/exceptions.py) to HTTP responses.

Registered once, in app/main.py's create_app(), so routers never need their
own try/except HTTPException blocks for these cases.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.exceptions import (
    AccountLockedError,
    AlreadyPaidError,
    AnalysisAlreadyExistsError,
    AnalysisNotCompletedError,
    AnalysisNotFoundError,
    CsrfRejectedError,
    CurrentPasswordIncorrectError,
    DisclaimerNotAcceptedError,
    EmailAlreadyVerifiedError,
    EmailDeliveryError,
    InvalidCredentialsError,
    InvalidWebhookSignatureError,
    OTPChallengeNotFoundError,
    OTPCooldownError,
    OTPExpiredError,
    OTPInvalidError,
    PaymentRequiredError,
    PhotoAngleUnknownError,
    PhotoNotFoundError,
    PhotoSetAlreadyCompleteError,
    PhotoSetNotReadyError,
    PhotoUploadInvalidError,
    QuestionnaireAnswersInvalidError,
    QuestionnaireNotSubmittedError,
    RefreshTokenExpiredError,
    RefreshTokenInvalidError,
    RefreshTokenReuseError,
    ReportImageNotFoundError,
    ReportNotFoundError,
    ResetTokenInvalidError,
    SamePasswordError,
    UnauthorizedError,
    WeakPasswordError,
)


def _error(code: str, message: str, **extra: object) -> dict:
    return {"error": {"code": code, "message": message, **extra}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(InvalidCredentialsError)
    async def _invalid_credentials(request: Request, exc: InvalidCredentialsError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=_error("INVALID_CREDENTIALS", "Invalid email or password."),
        )

    @app.exception_handler(EmailAlreadyVerifiedError)
    async def _email_already_verified(request: Request, exc: EmailAlreadyVerifiedError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_error("EMAIL_ALREADY_REGISTERED", "An account with this email already exists."),
        )

    @app.exception_handler(AccountLockedError)
    async def _account_locked(request: Request, exc: AccountLockedError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=_error(
                "ACCOUNT_LOCKED",
                "Too many failed attempts. Try again later.",
                retry_after_seconds=exc.retry_after_seconds,
            ),
        )

    @app.exception_handler(OTPCooldownError)
    async def _otp_cooldown(request: Request, exc: OTPCooldownError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=_error(
                "OTP_COOLDOWN",
                "Please wait before requesting another code.",
                retry_after_seconds=exc.retry_after_seconds,
            ),
        )

    @app.exception_handler(OTPChallengeNotFoundError)
    async def _otp_challenge_not_found(request: Request, exc: OTPChallengeNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=_error("OTP_CHALLENGE_NOT_FOUND", "This verification session is no longer valid."),
        )

    @app.exception_handler(OTPExpiredError)
    async def _otp_expired(request: Request, exc: OTPExpiredError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_error("OTP_EXPIRED", "This code has expired. Request a new one."),
        )

    @app.exception_handler(OTPInvalidError)
    async def _otp_invalid(request: Request, exc: OTPInvalidError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_error("OTP_INVALID", "Incorrect code."),
        )

    @app.exception_handler(RefreshTokenInvalidError)
    async def _refresh_invalid(request: Request, exc: RefreshTokenInvalidError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=_error("INVALID_TOKEN", "Invalid session."),
        )

    @app.exception_handler(RefreshTokenExpiredError)
    async def _refresh_expired(request: Request, exc: RefreshTokenExpiredError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=_error("TOKEN_EXPIRED", "Session expired. Please log in again."),
        )

    @app.exception_handler(RefreshTokenReuseError)
    async def _refresh_reuse(request: Request, exc: RefreshTokenReuseError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=_error("SESSION_REVOKED", "This session has been revoked. Please log in again."),
        )

    @app.exception_handler(CsrfRejectedError)
    async def _csrf_rejected(request: Request, exc: CsrfRejectedError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=_error("CSRF_REJECTED", "Request rejected by CSRF protection."),
        )

    @app.exception_handler(UnauthorizedError)
    async def _unauthorized(request: Request, exc: UnauthorizedError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=_error("UNAUTHORIZED", "Authentication required."),
        )

    @app.exception_handler(CurrentPasswordIncorrectError)
    async def _current_password_incorrect(request: Request, exc: CurrentPasswordIncorrectError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_error("CURRENT_PASSWORD_INCORRECT", str(exc)),
        )

    @app.exception_handler(SamePasswordError)
    async def _same_password(request: Request, exc: SamePasswordError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_error("SAME_PASSWORD", str(exc)),
        )

    @app.exception_handler(EmailDeliveryError)
    async def _email_delivery_failed(request: Request, exc: EmailDeliveryError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content=_error("EMAIL_DELIVERY_FAILED", "Could not send verification email. Please try again."),
        )

    @app.exception_handler(ResetTokenInvalidError)
    async def _reset_token_invalid(request: Request, exc: ResetTokenInvalidError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_error(
                "RESET_TOKEN_INVALID", "This reset link is invalid or has expired. Please request a new one."
            ),
        )

    @app.exception_handler(WeakPasswordError)
    async def _weak_password(request: Request, exc: WeakPasswordError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error("WEAK_PASSWORD", str(exc)),
        )

    @app.exception_handler(DisclaimerNotAcceptedError)
    async def _disclaimer_not_accepted(request: Request, exc: DisclaimerNotAcceptedError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error("DISCLAIMER_NOT_ACCEPTED", "You must accept the disclaimer before submitting."),
        )

    @app.exception_handler(QuestionnaireAnswersInvalidError)
    async def _questionnaire_answers_invalid(request: Request, exc: QuestionnaireAnswersInvalidError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error("QUESTIONNAIRE_ANSWERS_INVALID", str(exc), details=exc.details),
        )

    @app.exception_handler(PhotoAngleUnknownError)
    async def _photo_angle_unknown(request: Request, exc: PhotoAngleUnknownError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error("PHOTO_ANGLE_UNKNOWN", "Unknown photo angle."),
        )

    @app.exception_handler(PhotoUploadInvalidError)
    async def _photo_upload_invalid(request: Request, exc: PhotoUploadInvalidError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error("PHOTO_UPLOAD_INVALID", str(exc) or "Invalid photo upload."),
        )

    @app.exception_handler(PhotoSetAlreadyCompleteError)
    async def _photo_set_already_complete(request: Request, exc: PhotoSetAlreadyCompleteError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_error(
                "PHOTO_SET_ALREADY_COMPLETE",
                "Photos can't be changed after payment. Contact support if you need a new analysis.",
            ),
        )

    @app.exception_handler(PhotoNotFoundError)
    async def _photo_not_found(request: Request, exc: PhotoNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=_error("PHOTO_NOT_FOUND", "Photo not found."),
        )

    @app.exception_handler(PhotoSetNotReadyError)
    async def _photo_set_not_ready(request: Request, exc: PhotoSetNotReadyError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_error("PHOTO_SET_NOT_READY", "All required photos must pass validation before analysis."),
        )

    @app.exception_handler(QuestionnaireNotSubmittedError)
    async def _questionnaire_not_submitted(request: Request, exc: QuestionnaireNotSubmittedError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_error("QUESTIONNAIRE_NOT_SUBMITTED", "The onboarding questionnaire must be submitted first."),
        )

    @app.exception_handler(AnalysisAlreadyExistsError)
    async def _analysis_already_exists(request: Request, exc: AnalysisAlreadyExistsError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_error("ANALYSIS_ALREADY_EXISTS", "Analysis has already been started for this account."),
        )

    @app.exception_handler(AnalysisNotFoundError)
    async def _analysis_not_found(request: Request, exc: AnalysisNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=_error("ANALYSIS_NOT_FOUND", "Analysis not found."),
        )

    @app.exception_handler(AnalysisNotCompletedError)
    async def _analysis_not_completed(request: Request, exc: AnalysisNotCompletedError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_error(
                "ANALYSIS_NOT_COMPLETED", "Your facial analysis must complete before a report can be generated."
            ),
        )

    @app.exception_handler(ReportNotFoundError)
    async def _report_not_found(request: Request, exc: ReportNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=_error("REPORT_NOT_FOUND", "Report not found."),
        )

    @app.exception_handler(ReportImageNotFoundError)
    async def _report_image_not_found(request: Request, exc: ReportImageNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=_error("REPORT_IMAGE_NOT_FOUND", "No image is available for this feature."),
        )

    @app.exception_handler(AlreadyPaidError)
    async def _already_paid(request: Request, exc: AlreadyPaidError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_error("ALREADY_PAID", "You have already paid -- analysis will start automatically."),
        )

    @app.exception_handler(InvalidWebhookSignatureError)
    async def _invalid_webhook_signature(request: Request, exc: InvalidWebhookSignatureError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_error("INVALID_WEBHOOK_SIGNATURE", "Webhook signature verification failed."),
        )

    @app.exception_handler(PaymentRequiredError)
    async def _payment_required(request: Request, exc: PaymentRequiredError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            content=_error("PAYMENT_REQUIRED", "Payment is required before analysis can start."),
        )
