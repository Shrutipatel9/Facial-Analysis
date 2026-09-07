"""Per-IP rate limiting for auth endpoints.

Not client-specified, but necessary: the per-account OTP lockout (AUTH-011)
only throttles attacks against a single known account. Without this, an
attacker could still spam registrations or hammer /auth/login across many
different (or nonexistent) email addresses from one IP.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
