import { ApiError } from "./errors"

/**
 * True only when the backend has confirmed the refresh session itself is
 * unusable (missing/invalid/expired/revoked cookie). Network failures and
 * 5xx must NOT match -- those are temporary and must not log the user out.
 *
 * Backend refresh failures all map to HTTP 401 (see
 * app/exception_handlers.py: INVALID_TOKEN / TOKEN_EXPIRED / SESSION_REVOKED).
 */
export function isInvalidRefreshSessionError(err: unknown): boolean {
  return err instanceof ApiError && err.status === 401
}
