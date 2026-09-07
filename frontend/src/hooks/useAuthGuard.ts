"use client"

import { useRouter } from "next/navigation"
import { useEffect } from "react"

import { selectIsAuthenticated, selectIsAuthInitializing, useAuthStore } from "@/store/authStore"

/**
 * Client-side route protection. Next.js edge middleware CANNOT see this
 * app's auth state -- the access token and user object live only in the
 * in-memory Zustand store, not in anything middleware could read (the
 * refresh token is an httpOnly cookie, but that's opaque to the app and
 * only the backend ever reads it, docs/authentication.md §6) -- so this is
 * the only guard mechanism available, and it necessarily runs after the
 * shell has mounted.
 *
 * While `isAuthInitializing` (status === "idle") is true, AuthHydrator is
 * still restoring the session from the refresh cookie -- do NOT redirect.
 * Only a confirmed `unauthenticated` status redirects to /login.
 * Authentication is never inferred solely from whether `accessToken` is
 * currently non-null during startup.
 */
export function useAuthGuard(): { isChecking: boolean; isAuthInitializing: boolean } {
  const status = useAuthStore((state) => state.status)
  const isAuthInitializing = useAuthStore(selectIsAuthInitializing)
  const isAuthenticated = useAuthStore(selectIsAuthenticated)
  const router = useRouter()

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login")
    }
  }, [status, router])

  return {
    isAuthInitializing,
    // Keep waiting through both "still restoring" and the brief
    // pre-redirect instant after a confirmed logout / dead session.
    isChecking: isAuthInitializing || !isAuthenticated,
  }
}
