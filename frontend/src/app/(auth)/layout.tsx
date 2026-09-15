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
      router.replace("/home")
    }
  }, [isAuthenticated, router])

  // Wait out session restoration so a returning user does not briefly see
  // the login/signup form before being sent to the protected area --
  // useOnboardingEntryGuard (protected layout) sorts out where they
  // actually belong (questionnaire/photos/payment/analysis/home) once its
  // own checks resolve, so this only needs to land inside /home.
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
