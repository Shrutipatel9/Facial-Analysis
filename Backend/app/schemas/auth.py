import uuid
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.services.password_service import validate_password_strength

Purpose = Literal["signup", "login"]


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)

    @model_validator(mode="after")
    def _check_password_strength(self) -> "RegisterRequest":
        validate_password_strength(self.password, str(self.email))
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class OTPVerifyRequest(BaseModel):
    challenge_id: uuid.UUID
    # Exactly 6 digits -- malformed input (wrong length/non-numeric) is
    # rejected here, at the schema layer (422), before it ever reaches the
    # lockout/attempt-counting logic in otp_service.
    otp: str = Field(pattern=r"^\d{6}$")


class OTPResendRequest(BaseModel):
    challenge_id: uuid.UUID


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordVerifyRequest(BaseModel):
    email: EmailStr
    # Same shape as OTPVerifyRequest.otp -- malformed input rejected here,
    # before it can reach the lockout/attempt-counting logic.
    otp: str = Field(pattern=r"^\d{6}$")


class ResetPasswordVerifyResponse(BaseModel):
    # Proves OTP possession without re-exposing the raw code or completing
    # the reset -- see app/services/password_reset_service.py.
    reset_token: str
    expires_in: int


class ResetPasswordRequest(BaseModel):
    # No email/otp here -- reset_token (minted by /auth/reset-password/verify)
    # is the only proof of account access this request carries.
    reset_token: str = Field(min_length=1)
    new_password: str = Field(min_length=1, max_length=256)

    @model_validator(mode="after")
    def _check_password_strength(self) -> "ResetPasswordRequest":
        # Only the email-independent rules (length/letter/digit) can run
        # here -- there's no email in this request to check the
        # not-same-as-local-part rule against. That rule is re-checked,
        # email-aware, in password_reset_service.reset_password once
        # reset_token is decoded and the user is known (raises WeakPasswordError).
        validate_password_strength(self.new_password, "")
        return self


class ChallengeResponse(BaseModel):
    challenge_id: uuid.UUID
    purpose: Purpose
    otp_expiry_seconds: int
    # So the frontend's resend-button cooldown never has to hardcode/guess a
    # value that could drift from the backend's configured
    # OTP_RESEND_COOLDOWN_SECONDS.
    resend_cooldown_seconds: int


class ForgotPasswordResponse(BaseModel):
    # Deliberately generic and identical regardless of whether the email
    # exists (see password_reset_service.request_password_reset) -- no
    # challenge_id here, unlike ChallengeResponse, since a challenge_id
    # would itself reveal account existence by its mere presence/absence.
    # otp_expiry_seconds/resend_cooldown_seconds are static config, not
    # account-specific, so including them always is safe.
    message: str
    otp_expiry_seconds: int
    resend_cooldown_seconds: int


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    verification_status: str

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    # No refresh_token field -- it never enters the JSON body or JS-readable
    # state at all (v1.4). The backend sets it directly as an httpOnly,
    # Secure cookie (see routers/auth.py's _set_refresh_cookie) in the same
    # response that carries this body.
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserOut


class RefreshResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    # Included so AuthHydrator can restore Zustand in one round-trip after
    # reload (no separate GET /auth/me that could race another refresh).
    user: UserOut


class MessageResponse(BaseModel):
    message: str
