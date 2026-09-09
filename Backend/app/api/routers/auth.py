"""Authentication endpoints -- thin: all business logic lives in
app/services/*. See docs/authentication.md for the full flow spec.
"""

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_cookie_csrf
from app.core.config import Settings, get_settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.exceptions import EmailAlreadyVerifiedError, InvalidCredentialsError, RefreshTokenInvalidError
from app.models.otp_record import OTPRecord
from app.models.user import User
from app.schemas.auth import (
    ChallengeResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    MessageResponse,
    OTPResendRequest,
    OTPVerifyRequest,
    RefreshResponse,
    RegisterRequest,
    ResetPasswordRequest,
    ResetPasswordVerifyRequest,
    ResetPasswordVerifyResponse,
    TokenResponse,
    UserOut,
)
from app.services import jwt_service, otp_service, password_reset_service, user_service
from app.services.password_service import verify_login_password

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_NAME = "refresh_token"


def _challenge_response(record: OTPRecord) -> ChallengeResponse:
    settings = get_settings()
    return ChallengeResponse(
        challenge_id=record.id,
        purpose=record.purpose,  # type: ignore[arg-type]
        otp_expiry_seconds=settings.otp_expire_minutes * 60,
        resend_cooldown_seconds=settings.otp_resend_cooldown_seconds,
    )


def _set_refresh_cookie(response: Response, raw_refresh_token: str, settings: Settings) -> None:
    """httpOnly refresh cookie. SameSite=Strict is correct for the same-origin
    Next.js proxy model (cookie is first-party on the frontend origin and only
    needed for XHR to that origin). Secure follows ENVIRONMENT."""
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
        max_age=settings.refresh_token_expire_days * 86400,
    )


def _clear_refresh_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
    )


@router.post("/register", response_model=ChallengeResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
async def register(
    request: Request, payload: RegisterRequest, db: AsyncSession = Depends(get_db)
) -> ChallengeResponse:
    existing = await user_service.get_by_email(db, payload.email)

    if existing is not None and existing.verification_status == "verified":
        raise EmailAlreadyVerifiedError()

    if existing is not None:
        # Registered but never verified: treat this as a fresh attempt
        # rather than a duplicate-email error (the user likely abandoned
        # signup last time, or mistyped their password and is retrying).
        user = await user_service.restart_pending_signup(
            db, existing, password=payload.password, full_name=payload.full_name
        )
    else:
        user = await user_service.create_pending_user(
            db, email=str(payload.email), password=payload.password, full_name=payload.full_name
        )

    record = await otp_service.request_otp(db, user, "signup")
    return _challenge_response(record)


@router.post("/login", response_model=ChallengeResponse)
@limiter.limit("20/minute")
async def login(request: Request, payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> ChallengeResponse:
    user = await user_service.get_by_email(db, payload.email)

    if user is None:
        # Run a real (dummy) password verification anyway so response time
        # doesn't reveal whether the email exists (anti-enumeration).
        from app.core.security import verify_password_dummy

        verify_password_dummy()
        raise InvalidCredentialsError()

    if not verify_login_password(payload.password, user.password_hash):
        raise InvalidCredentialsError()

    # An unverified account logging in is routed back into completing
    # signup (purpose="signup") rather than a bare auth error -- they know
    # their password, they just never finished OTP verification.
    purpose = "signup" if user.verification_status != "verified" else "login"
    record = await otp_service.request_otp(db, user, purpose)
    return _challenge_response(record)


@router.post("/otp/verify", response_model=TokenResponse)
@limiter.limit("10/minute")
async def verify_otp(
    request: Request, payload: OTPVerifyRequest, response: Response, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    user = await otp_service.verify_otp(db, str(payload.challenge_id), payload.otp)

    if user.verification_status != "verified":
        await user_service.mark_verified(db, user)

    tokens = await jwt_service.issue_token_pair(db, user)
    _set_refresh_cookie(response, tokens.refresh_token, get_settings())
    return TokenResponse(
        access_token=tokens.access_token,
        expires_in=tokens.expires_in,
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)) -> UserOut:
    """Lets the frontend recover the user object after a page reload, once
    it's exchanged the httpOnly refresh cookie for a fresh access token via
    /auth/refresh (that response carries tokens only, not the user)."""
    return UserOut.model_validate(current_user)


@router.post("/change-password", response_model=MessageResponse)
@limiter.limit("10/minute")
async def change_password(
    request: Request,
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """In-app password change (FR-017) -- see ChangePasswordRequest's
    docstring for why this does not sign the user out, unlike
    /auth/reset-password."""
    await user_service.change_password(
        db, current_user, current_password=payload.current_password, new_password=payload.new_password
    )
    await db.commit()
    return MessageResponse(message="Password changed.")


@router.post("/otp/resend", response_model=ChallengeResponse)
@limiter.limit("5/minute")
async def resend_otp(
    request: Request, payload: OTPResendRequest, db: AsyncSession = Depends(get_db)
) -> ChallengeResponse:
    record = await otp_service.resend_otp(db, str(payload.challenge_id))
    return _challenge_response(record)


@router.post("/refresh", response_model=RefreshResponse)
@limiter.limit("30/minute")
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    _csrf: None = Depends(require_cookie_csrf),
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
) -> RefreshResponse:
    if refresh_token is None:
        raise RefreshTokenInvalidError()
    tokens = await jwt_service.rotate_refresh_token(db, refresh_token)
    _set_refresh_cookie(response, tokens.refresh_token, get_settings())
    return RefreshResponse(
        access_token=tokens.access_token,
        expires_in=tokens.expires_in,
        user=UserOut.model_validate(tokens.user),
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    _csrf: None = Depends(require_cookie_csrf),
    _current_user: User = Depends(get_current_user),
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
) -> MessageResponse:
    if refresh_token is not None:
        await jwt_service.revoke_current_session(db, refresh_token)
    _clear_refresh_cookie(response, get_settings())
    return MessageResponse(message="Logged out.")


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
@limiter.limit("5/hour")
async def forgot_password(
    request: Request, payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)
) -> ForgotPasswordResponse:
    # Always the same response, whether or not the email exists --
    # password_reset_service silently no-ops for a nonexistent account. The
    # response never carries anything account-specific (no challenge_id),
    # so its shape can't be used to enumerate accounts either.
    await password_reset_service.request_password_reset(db, str(payload.email))
    settings = get_settings()
    return ForgotPasswordResponse(
        message="If an account exists for this email, we've sent a password reset code.",
        otp_expiry_seconds=settings.otp_expire_minutes * 60,
        resend_cooldown_seconds=settings.otp_resend_cooldown_seconds,
    )


@router.post("/reset-password/verify", response_model=ResetPasswordVerifyResponse)
@limiter.limit("10/minute")
async def verify_reset_password_otp(
    request: Request, payload: ResetPasswordVerifyRequest, db: AsyncSession = Depends(get_db)
) -> ResetPasswordVerifyResponse:
    reset_token, expires_in = await password_reset_service.verify_reset_otp(
        db, email=str(payload.email), otp=payload.otp
    )
    return ResetPasswordVerifyResponse(reset_token=reset_token, expires_in=expires_in)


@router.post("/reset-password", response_model=MessageResponse)
@limiter.limit("10/minute")
async def reset_password(
    request: Request, payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    await password_reset_service.reset_password(
        db, reset_token=payload.reset_token, new_password=payload.new_password
    )
    return MessageResponse(message="Password reset. Please log in with your new password.")
