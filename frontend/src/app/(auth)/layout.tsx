"use client"

import { Loader2 } from "lucide-react"
import { useRouter } from "next/navigation"
import { useEffect } from "react"

import { selectIsAuthenticated, selectIsAuthInitializing, useAuthStore } from "@/store/authStore"

export default function AuthRouteGroupLayout({ children }: { children: React.ReactNode }) {
  const isAuthInitializing = useAuthStore(selectIsAuthInitializing)
  const isAuthenticated = useAuthStore(selectIsAuthenticated)
  const router = useRouter()

  useEffect(() => {
    if (isAuthenticated) {
      router.replace("/dashboard")
    }
  }, [isAuthenticated, router])

  // Wait out session restoration so a returning user does not briefly see
  // the login/signup form before being sent to the dashboard.
  if (isAuthInitializing) {
    return (
      <div className="flex min-h-svh items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" aria-label="Loading" />
      </div>
    )
  }

  if (isAuthenticated) {
    return (
      <div className="flex min-h-svh items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" aria-label="Loading" />
      </div>
    )
  }

  return <>{children}</>
}
