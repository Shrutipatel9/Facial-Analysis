/**
 * Module-level auth session owner.
 *
 * Access token → Zustand (memory only).
 * Refresh token → httpOnly cookie (set by backend; browser sends it via the
 * same-origin `/api/backend` proxy).
 *
 * Critical invariants:
 * - Exactly one in-flight refresh / bootstrap at a time (React Strict Mode
 *   remounts and concurrent 401s must share the same promise — parallel
 *   refreshes race cookie rotation and can revoke the whole token family).
 * - Access-token expiry never clears auth.
 * - Only explicit logout or a confirmed refresh 401 clears auth.
 * - Network / 5xx never clear auth.
 */

import { API_BASE_URL } from "@/lib/env"
import { ApiError, NetworkError } from "@/lib/api/errors"
import { isInvalidRefreshSessionError } from "@/lib/api/sessionErrors"
import { useAuthStore, type AuthUser } from "@/store/authStore"

export interface SessionTokens {
  access_token: string
  token_type: "bearer"
  expires_in: number
  user: AuthUser
}

interface BackendErrorBody {
  error: { code: string; message: string; retry_after_seconds?: number }
}

let refreshPromise: Promise<SessionTokens> | null = null
let bootstrapPromise: Promise<void> | null = null
let bootstrapped = false

async function rawFetch(path: string, init: RequestInit): Promise<Response> {
  try {
    const headers = new Headers(init.headers)
    // Required by backend cookie-CSRF checks (app/core/csrf.py). Blocks
    // simple cross-site form posts that cannot set custom headers.
    if (!headers.has("X-Requested-With")) {
      headers.set("X-Requested-With", "XMLHttpRequest")
    }

    return await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers,
      credentials: "include",
    })
  } catch (cause) {
    throw new NetworkError(cause)
  }
}

async function toResult<T>(response: Response): Promise<T> {
  if (response.ok) {
    const text = await response.text()
    return (text ? JSON.parse(text) : undefined) as T
  }

  let body: BackendErrorBody | null = null
  try {
    body = await response.json()
  } catch {
    body = null
  }

  throw new ApiError(
    response.status,
    body?.error?.code ?? "UNKNOWN_ERROR",
    body?.error?.message ?? `Request failed with status ${response.status}.`,
    body?.error?.retry_after_seconds
  )
}

function applySession(tokens: SessionTokens): void {
  useAuthStore.getState().setSession({
    user: tokens.user,
    accessToken: tokens.access_token,
    expiresIn: tokens.expires_in,
  })
}

async function performRefresh(): Promise<SessionTokens> {
  try {
    const response = await rawFetch("/auth/refresh", {
      method: "POST",
    })
    const tokens = await toResult<SessionTokens>(response)
    applySession(tokens)
    return tokens
  } catch (err) {
    if (isInvalidRefreshSessionError(err)) {
      useAuthStore.getState().clearSession()
    }
    throw err
  }
}

/**
 * Single-flight access-token refresh. Used by proactive scheduler and by
 * the 401 retry path. Always goes through this function — never call
 * `/auth/refresh` from elsewhere.
 */
export function refreshSession(): Promise<SessionTokens> {
  refreshPromise ??= performRefresh().finally(() => {
    refreshPromise = null
  })
  return refreshPromise
}

/**
 * Restore auth after a full page load. Module-scoped so React Strict Mode
 * remounts share one attempt instead of racing two cookie rotations.
 *
 * - 401 from refresh → unauthenticated (no cookie / revoked / expired)
 * - network / 5xx → stay idle and retry (never treat as logout)
 */
export function bootstrapSession(): Promise<void> {
  if (bootstrapped && useAuthStore.getState().status !== "idle") {
    return Promise.resolve()
  }

  bootstrapPromise ??= (async () => {
    let delayMs = 1_000

    while (useAuthStore.getState().status === "idle") {
      try {
        await refreshSession()
        bootstrapped = true
        return
      } catch (err) {
        if (isInvalidRefreshSessionError(err)) {
          // clearSession already ran inside performRefresh
          bootstrapped = true
          return
        }

        await new Promise<void>((resolve) => {
          setTimeout(resolve, delayMs)
        })
        delayMs = Math.min(delayMs * 2, 30_000)
      }
    }

    bootstrapped = true
  })().finally(() => {
    bootstrapPromise = null
  })

  return bootstrapPromise
}

/** Establish session after OTP success (cookie already set by that response). */
export function establishSession(tokens: SessionTokens): void {
  applySession(tokens)
  bootstrapped = true
}

/** Explicit logout: revoke server session, clear cookie, clear Zustand. */
export async function logoutSession(): Promise<void> {
  const { accessToken, clearSession } = useAuthStore.getState()

  try {
    await rawFetch("/auth/logout", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
    })
  } catch {
    // Best-effort revoke — always clear local state afterward.
  } finally {
    clearSession()
    bootstrapped = true
  }
}

export async function publicRequest<T>(path: string, body?: unknown): Promise<T> {
  const response = await rawFetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  return toResult<T>(response)
}

export async function authenticatedRequest<T>(
  path: string,
  options: { method?: string; body?: unknown } = {}
): Promise<T> {
  const buildInit = (): RequestInit => {
    const { accessToken } = useAuthStore.getState()
    return {
      method: options.method ?? "POST",
      headers: {
        "Content-Type": "application/json",
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    }
  }

  let response = await rawFetch(path, buildInit())

  if (response.status === 401) {
    try {
      await refreshSession()
    } catch (err) {
      if (isInvalidRefreshSessionError(err)) {
        return toResult<T>(response)
      }
      throw err
    }
    response = await rawFetch(path, buildInit())
  }

  return toResult<T>(response)
}

export async function checkBackendHealth(): Promise<{ status: string }> {
  const response = await rawFetch("/health", { method: "GET" })
  return toResult<{ status: string }>(response)
}
