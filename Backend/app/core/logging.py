"""Structured logging setup with a redaction filter.

Password, OTP, and token values must never reach log output in plaintext
(AUTH-011, docs/security.md §2). The redaction filter below is a defense-in-depth
guard: application code should still avoid logging secrets directly, but a bug
that does so should not result in a leaked secret in log storage.
"""

import logging
import re
import sys

_SENSITIVE_KEYS = (
    "password",
    "otp",
    "otp_hash",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "otp_pepper",
    "jwt_secret",
)

# Matches: "key": "value" | 'key': 'value' | key=value | key: value
# for any of the sensitive key names above, case-insensitive.
_KEYS_ALTERNATION = "|".join(_SENSITIVE_KEYS)
# %-formatting used deliberately here (not str.format()/f-string): the
# pattern's literal `{`/`}` (from the `[^"'\s,}]+` char class) would each
# need doubling to escape them from format()'s own brace syntax, which reads
# worse than the substitution it's avoiding.
_REDACT_PATTERN = re.compile(
    r"""(?P<prefix>["']?(?:%s)["']?\s*[:=]\s*)(?P<quote>["']?)(?P<value>[^"'\s,}]+)(?P=quote)""" % _KEYS_ALTERNATION,  # noqa: UP031
    re.IGNORECASE,
)

# Matches the "Bearer <token>" shape of an Authorization header value
# specifically, since that doesn't fit the key=value/key: value shape above.
_BEARER_PATTERN = re.compile(r"(?P<prefix>\bBearer\s+)(?P<value>\S+)", re.IGNORECASE)

REDACTED = "***REDACTED***"


def redact(text: str) -> str:
    # Bearer-token pattern first: it must see the literal word "Bearer"
    # before the key=value pass below has a chance to consume it as if it
    # were itself the redactable value (e.g. "Authorization: Bearer ...").
    text = _BEARER_PATTERN.sub(lambda m: f"{m.group('prefix')}{REDACTED}", text)
    text = _REDACT_PATTERN.sub(lambda m: f"{m.group('prefix')}{m.group('quote')}{REDACTED}{m.group('quote')}", text)
    return text


class RedactingFilter(logging.Filter):
    """Redacts sensitive key/value pairs from log records before they're emitted."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: (redact(v) if isinstance(v, str) else v) for k, v in record.args.items()}
            else:
                record.args = tuple(redact(a) if isinstance(a, str) else a for a in record.args)
        return True


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RedactingFilter())
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]
