import { create } from "zustand"

export interface AuthUser {
  id: string
  email: string
  role: string
  verification_status: "pending" | "verified"
}

/**
 * "idle" means "not yet determined" -- either the very first render or
 * mid-restoration (see AuthHydrator). Guards (useAuthGuard, the (auth)
 * route group, "/") must treat "idle" as "still loading, don't decide
 * yet", NOT as "unauthenticated" -- conflating the two would redirect a
 * returning, still-logged-in user to /login before AuthHydrator even had a
 * chance to restore their session from the refresh cookie.
 *
 * Equivalent names used in product language:
 * - isAuthInitializing  ↔  status === "idle"
 * - isAuthenticated     ↔  status === "authenticated"
 */
export type AuthStatus = "idle" | "authenticated" | "unauthenticated"

interface AuthState {
  user: AuthUser | null
  accessToken: string | null
  /** Epoch ms when the current access token is expected to expire. */
  accessTokenExpiresAt: number | null
  status: AuthStatus

  setSession: (session: { user: AuthUser; accessToken: string; expiresIn: number }) => void
  updateAccessToken: (accessToken: string, expiresIn: number) => void
  clearSession: () => void
}

export const selectIsAuthInitializing = (state: AuthState) => state.status === "idle"
export const selectIsAuthenticated = (state: AuthState) => state.status === "authenticated"

/**
 * The Vuex/Redux-equivalent single store for this app's auth state
 * (docs/architecture.md's UI -> Zustand Auth Store -> API Client ->
 * Backend Auth APIs layering).
 *
 * Token storage (v1.4, supersedes FE-002/ASM-001's original "both tokens in
 * Zustand" decision): the refresh token no longer lives in this store, or
 * in any JS-readable browser storage, at all -- it travels exclusively as
 * an httpOnly cookie the backend sets/reads directly
 * (app/api/routers/auth.py's _set_refresh_cookie), so no script on this
 * page can ever read or exfiltrate it. Only the short-lived access token
 * and user object live here, in plain memory -- deliberately NOT wrapped
 * in Zustand's `persist` middleware, so nothing token-related ever touches
 * sessionStorage/localStorage either. "Stay logged in" across a page
 * reload or browser restart comes entirely from the cookie (see
 * AuthHydrator), not from anything this store persists client-side.
 *
 * Access-token expiry alone must NEVER clear this store. Clearing happens
 * only on explicit logout or a backend-confirmed invalid refresh session.
 *
 * Only Client Components read this store -- there is no server-side code
 * in this project that could read it anyway (Next.js here is
 * frontend-only, see CLAUDE.md).
 */
export const useAuthStore = create<AuthState>()((set) => ({
  user: null,
  accessToken: null,
  accessTokenExpiresAt: null,
  status: "idle",

  setSession: ({ user, accessToken, expiresIn }) =>
    set({
      user,
      accessToken,
      accessTokenExpiresAt: Date.now() + expiresIn * 1000,
      status: "authenticated",
    }),

  updateAccessToken: (accessToken, expiresIn) =>
    set({
      accessToken,
      accessTokenExpiresAt: Date.now() + expiresIn * 1000,
    }),

  clearSession: () =>
    set({
      user: null,
      accessToken: null,
      accessTokenExpiresAt: null,
      status: "unauthenticated",
    }),
}))
