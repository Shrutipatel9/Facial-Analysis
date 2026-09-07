import { refreshSession } from "@/lib/auth/authSession"
import { isInvalidRefreshSessionError } from "@/lib/api/sessionErrors"
import { useAuthStore } from "@/store/authStore"

/** Refresh ~1 minute before access-token expiry (AUTH-012: 15 min lifetime). */
const REFRESH_SKEW_MS = 60_000
const MIN_DELAY_MS = 5_000
const TRANSIENT_RETRY_MS = 30_000

let timer: ReturnType<typeof setTimeout> | null = null
let unsubscribe: (() => void) | null = null

function clearScheduledRefresh() {
  if (timer !== null) {
    clearTimeout(timer)
    timer = null
  }
}

export function scheduleAccessTokenRefresh(expiresInSeconds: number) {
  clearScheduledRefresh()

  const delayMs = Math.max(expiresInSeconds * 1000 - REFRESH_SKEW_MS, MIN_DELAY_MS)

  timer = setTimeout(async () => {
    timer = null

    if (useAuthStore.getState().status !== "authenticated") return

    try {
      const result = await refreshSession()
      scheduleAccessTokenRefresh(result.expires_in)
    } catch (err) {
      if (isInvalidRefreshSessionError(err)) return

      timer = setTimeout(() => {
        timer = null
        scheduleAccessTokenRefresh(REFRESH_SKEW_MS / 1000)
      }, TRANSIENT_RETRY_MS)
    }
  }, delayMs)
}

export function startTokenRefreshScheduler() {
  if (unsubscribe) return

  unsubscribe = useAuthStore.subscribe((state, prev) => {
    if (state.status === "unauthenticated") {
      clearScheduledRefresh()
      return
    }

    if (
      state.status === "authenticated" &&
      state.accessTokenExpiresAt !== null &&
      state.accessTokenExpiresAt !== prev.accessTokenExpiresAt
    ) {
      const expiresInSeconds = Math.max((state.accessTokenExpiresAt - Date.now()) / 1000, 0)
      scheduleAccessTokenRefresh(expiresInSeconds)
    }
  })
}
