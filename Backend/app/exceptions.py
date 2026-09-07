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
