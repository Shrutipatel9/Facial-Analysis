"""Error-tracking integration (Milestone 3.1, Phase 23 -- production
hardening). Sentry by default (the common FastAPI + Next.js pairing), but
this module is the one place that decision lives -- swapping vendors later
is a rewrite of this file only, same "one seam, not scattered vendor calls"
convention as app/services/email_service.py's EmailSender.

Inert unless settings.sentry_dsn is set: init_error_tracking() is always
called at startup (app/main.py), but does nothing at all without a DSN --
no vendor account is created or required by this codebase, and no
behavior changes for a deployment that never sets SENTRY_DSN. This lets
the wiring land now and be activated later purely by provisioning an
account and setting one env var, not a code change.
"""

import logging

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.types import Event, Hint

from app.core.config import get_settings
from app.core.logging import redact

logger = logging.getLogger(__name__)


def _redact_event_strings(event: Event, hint: Hint) -> Event | None:  # noqa: ARG001 -- hint required by Sentry's callback signature
    """Best-effort redaction of the event's own free-text fields (exception
    messages, log message, breadcrumb messages) before it leaves the
    process -- reuses the exact same redact() already proven for stdout
    logging (app/core/logging.py) rather than a second, divergent
    scrubbing implementation. Not a full recursive walk of the event's
    request/context data (Sentry's own `send_default_pii=False`, set
    below, is what actually keeps request bodies/headers/cookies out of
    the event in the first place -- this only covers the message text
    Sentry always captures regardless of that setting)."""
    message = event.get("message")
    if isinstance(message, str):
        event["message"] = redact(message)

    for exc_value in event.get("exception", {}).get("values", []):
        if isinstance(exc_value.get("value"), str):
            exc_value["value"] = redact(exc_value["value"])

    breadcrumbs = event.get("breadcrumbs")
    if isinstance(breadcrumbs, dict):
        for crumb in breadcrumbs.get("values", []):
            if isinstance(crumb.get("message"), str):
                crumb["message"] = redact(crumb["message"])

    return event


def init_error_tracking() -> None:
    settings = get_settings()
    if not settings.sentry_dsn:
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        integrations=[FastApiIntegration()],
        # Never send request bodies/headers/cookies/user PII by default --
        # same privacy posture as this project's existing logging redaction
        # (docs/security.md), just enforced at the SDK-config level here
        # instead of a regex pass. _redact_event_strings below is a second,
        # narrower layer over the message text this setting doesn't cover.
        send_default_pii=False,
        before_send=_redact_event_strings,
    )
    logger.info("Error tracking initialized (environment=%s)", settings.environment)
