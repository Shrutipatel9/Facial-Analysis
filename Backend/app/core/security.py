"""Low-level cryptographic primitives. No DB access, no business rules --
just hashing/encoding/decoding building blocks used by the services layer.
"""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

_password_hasher = PasswordHash.recommended()  # Argon2id -- see docs/security.md §7


# --- Passwords ---
# Argon2id (via pwdlib) was chosen over bcrypt specifically because bcrypt
# silently truncates input at 72 bytes -- a real footgun where a user's
# actual entropy-bearing tail of a long passphrase is silently ignored.
# Argon2 has no such truncation.


def hash_password(plain_password: str) -> str:
    return _password_hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return _password_hasher.verify(plain_password, password_hash)


# A fixed, validly-formatted Argon2id hash of a random value, used to run a
# real verify() against nonexistent-email login attempts so the response
# time doesn't leak whether the email exists (anti-enumeration).
_DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(32))


def verify_password_dummy() -> None:
    verify_password(secrets.token_urlsafe(16), _DUMMY_PASSWORD_HASH)


# --- OTP codes ---
# HMAC-SHA256 with a server-side pepper, not Argon2: OTP brute force is
# already bounded by the 5-attempt/15-minute lockout (AUTH-011), not by hash
# cost, so a slow hash here would only add latency to every verify call for
# no security benefit.


def generate_otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp_code(code: str) -> str:
    settings = get_settings()
    return hmac.new(settings.otp_pepper.encode(), code.encode(), hashlib.sha256).hexdigest()


def verify_otp_code(code: str, otp_hash: str) -> bool:
    return hmac.compare_digest(hash_otp_code(code), otp_hash)


# --- Refresh tokens ---
# The raw token is an opaque random string, not a JWT -- rotation/revocation
# require a DB lookup anyway, so encoding it as a self-verifying JWT would
# add nothing but the temptation to skip that lookup (AUTH-010).


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


# --- Access tokens (JWT) ---


def create_access_token(*, subject: str, role: str, expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    payload = {"sub": subject, "role": role, "purpose": "access", "exp": expire, "iat": datetime.now(UTC)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    # Algorithm is explicitly pinned here -- never derived from the token's
    # own header -- to prevent algorithm-confusion attacks.
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


# --- Purpose-scoped tokens (e.g. password reset) ---
# Same signing secret/algorithm as access tokens, but carry a "purpose"
# claim other than "access" -- get_current_user (app/api/deps.py) rejects
# any token whose purpose isn't "access", so these can never be used as a
# Bearer credential no matter how long their TTL is.


def create_purpose_token(*, subject: str, purpose: str, expires_delta: timedelta, **extra_claims: str) -> str:
    settings = get_settings()
    expire = datetime.now(UTC) + expires_delta
    payload: dict[str, Any] = {"sub": subject, "purpose": purpose, "exp": expire, "iat": datetime.now(UTC)}
    payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def hash_reset_binding(password_hash: str) -> str:
    """Non-reversible fingerprint of a user's CURRENT password hash, embedded
    in a password-reset token so it self-invalidates the instant the
    password actually changes -- gives the token single-use semantics
    without a server-side token table. Only ever compared for equality."""
    return hashlib.sha256(password_hash.encode()).hexdigest()[:32]
