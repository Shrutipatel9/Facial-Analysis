"use client"

import { useEffect } from "react"

import { bootstrapSession } from "@/lib/auth/authSession"
import { startTokenRefreshScheduler } from "@/lib/auth/tokenRefreshScheduler"

/**
 * Mounted once in the root layout. Kicks off module-level session restore.
 *
 * Intentionally does NOT cancel the in-flight bootstrap on unmount — React
 * Strict Mode remounts must share the same single-flight promise in
 * authSession, not abort and restart a second cookie rotation.
 */
export function AuthHydrator() {
  useEffect(() => {
    startTokenRefreshScheduler()
    void bootstrapSession()
  }, [])

  return null
}
