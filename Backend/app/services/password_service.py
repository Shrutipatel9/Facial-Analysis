"""Password hashing + strength validation.

Password rules are not client-specified (docs/security.md §7 flags this as
an open delivery-team decision) -- these are sensible defaults, not a
client requirement, and can be revisited without touching the auth flow
itself.
"""

import re

from app.core.security import hash_password, verify_password

MIN_LENGTH = 10
MAX_LENGTH = 128


def validate_password_strength(password: str, email: str) -> None:
    if len(password) < MIN_LENGTH:
        raise ValueError(f"Password must be at least {MIN_LENGTH} characters long.")
    if len(password) > MAX_LENGTH:
        raise ValueError(f"Password must be at most {MAX_LENGTH} characters long.")
    if not re.search(r"[A-Za-z]", password):
        raise ValueError("Password must contain at least one letter.")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one number.")

    local_part = email.split("@", 1)[0].strip().lower()
    if local_part and password.lower() == local_part:
        raise ValueError("Password must not be the same as your email address.")


def hash_new_password(password: str) -> str:
    # Argon2 (via pwdlib) has no silent-truncation behavior, unlike bcrypt --
    # the full password is hashed, not just its first 72 bytes.
    return hash_password(password)


def verify_login_password(password: str, password_hash: str) -> bool:
    return verify_password(password, password_hash)
