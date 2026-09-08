"""Domain exceptions for the authentication module.

Services raise these; app/exception_handlers.py maps them to HTTP responses.
Keeping the mapping out of services/routers means a service function's
control flow reads as business logic, not HTTP status codes.
"""


class DomainError(Exception):
    """Base class for all domain exceptions."""


class InvalidCredentialsError(DomainError):
    """Email/password did not match. Message is deliberately generic --
    never reveal whether the email exists (anti-enumeration)."""


class UnauthorizedError(DomainError):
    """Missing/malformed/expired/invalid access token on a protected route.
    A single generic case is enough here: the frontend's API client reacts
    to the 401 status itself (triggering a silent refresh-and-retry), not
    to a specific error code -- fine-grained codes matter on /auth/refresh's
    own response, not on every protected endpoint."""


class EmailAlreadyVerifiedError(DomainError):
    """Signup attempted against an email that is already a verified account."""


class AccountLockedError(DomainError):
    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__("Account is temporarily locked due to too many failed OTP attempts.")


class OTPCooldownError(DomainError):
    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__("An OTP was already sent recently; please wait before requesting another.")


class OTPChallengeNotFoundError(DomainError):
    """The challenge_id is unknown, or has been superseded by a newer OTP
    request -- deliberately not distinguished from "wrong/expired attempt"
    in a way that would let a caller enumerate valid challenge ids."""


class OTPExpiredError(DomainError):
    """The OTP existed and matched the challenge, but its expiry has
    passed. Does NOT count as a failed attempt (docs/authentication.md)."""


class OTPInvalidError(DomainError):
    """The submitted code does not match. Counts as a failed attempt."""


class RefreshTokenInvalidError(DomainError):
    """Unknown or malformed refresh token."""


class RefreshTokenExpiredError(DomainError):
    """A known, never-reused refresh token whose expiry has passed. NOT a
    reuse event -- must not trigger family revocation."""


class RefreshTokenReuseError(DomainError):
    """A refresh token that was already rotated out has been presented
    again -- the entire token family has just been revoked as a
    precaution. The single highest-risk case in this module."""


class CsrfRejectedError(DomainError):
    """Cookie-authenticated request failed Origin / X-Requested-With checks."""


class EmailDeliveryError(DomainError):
    """The configured EmailSender failed to send. Callers must not report
    success to the client when this is raised."""


class SamePasswordError(DomainError):
    """Password-reset attempted with a new password identical to the
    current one. Only ever raised *after* OTP verification already
    succeeded (see password_reset_service.reset_password) -- by that point
    the caller has already proven access to the account, so this is not an
    enumeration concern the way other reset errors are."""

    def __init__(self) -> None:
        super().__init__("New password must be different from your current password.")


class ResetTokenInvalidError(DomainError):
    """The reset_token on POST /auth/reset-password is missing, malformed,
    expired, wrong-purpose, or already redeemed (single-use, enforced via
    the password-hash fingerprint claim -- see hash_reset_binding). All
    collapsed into one generic case; by this point the caller already
    proved account access via OTP, so there's no anti-enumeration reason to
    distinguish sub-cases."""


class WeakPasswordError(DomainError):
    """New password fails the same strength rules enforced at signup --
    raised here (not by a schema validator) because ResetPasswordRequest no
    longer carries the user's email (only reset_token + new_password), so
    the email-aware half of validate_password_strength can only run after
    the token is decoded and the user resolved."""


class DisclaimerNotAcceptedError(DomainError):
    """POST /questionnaire/responses with disclaimer_accepted != true.
    BR-003 is a hard, non-optional gate -- must be re-validated here even
    though the frontend also disables Submit client-side."""


class QuestionnaireAnswersInvalidError(DomainError):
    """A required, currently-visible question is missing/empty, an answer
    doesn't match its question's type/allowed options, or the payload
    contains a key that isn't a known question id at all. Carries the
    offending question id(s)/reason so the frontend can highlight the right
    step -- see app/services/questionnaire_service._validate_and_clean."""

    def __init__(self, details: list[dict[str, str]]) -> None:
        self.details = details
        super().__init__("One or more questionnaire answers are invalid.")


class PhotoAngleUnknownError(DomainError):
    """POST /photos with an `angle` that isn't in REQUIRED_ANGLES."""


class PhotoUploadInvalidError(DomainError):
    """The upload request itself is malformed -- missing file, wrong
    content-type, or over PHOTO_MAX_UPLOAD_BYTES. Distinct from a photo
    that decodes fine but fails a quality check (BR-005) -- that is not an
    error, see photo_service.upload_photo."""


class PhotoSetAlreadyCompleteError(DomainError):
    """Upload attempted after every required angle already has a passed
    photo (BR-004). A user who wants to redo a photo after full completion
    isn't a supported flow in this phase -- one-and-done, same posture as
    the questionnaire's no-resubmission rule."""


class PhotoNotFoundError(DomainError):
    """GET /photos/{id} for an id that doesn't exist or isn't owned by the
    caller -- collapsed into one generic case, same anti-enumeration
    posture as other not-found cases in this codebase."""
