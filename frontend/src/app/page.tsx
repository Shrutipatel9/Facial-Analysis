"use client"

import { Loader2 } from "lucide-react"
import { useRouter } from "next/navigation"
import { useEffect } from "react"

import { useAuthStore } from "@/store/authStore"

/**
 * No marketing landing page exists yet (that's the separate `landing-page`
 * module, Phase 2 of docs/phase-wise-requirements.md) -- until then, "/"
 * acts as an auth-aware entry gate rather than showing dead placeholder
 * content: signed-out visitors go straight to signup, signed-in users go
 * to their dashboard. Same redirect-on-mount pattern as
 * app/(auth)/layout.tsx and app/(protected)/layout.tsx.
 *
 * Waits out "idle" (AuthHydrator still restoring/validating a possibly
 * recovered session) before deciding -- redirecting immediately would send
 * a returning, still-logged-in user to /signup for an instant on every
 * load, before their session had a chance to be confirmed.
 */
export default function RootPage() {
  const status = useAuthStore((state) => state.status)
  const router = useRouter()

  useEffect(() => {
    if (status === "idle") return
    router.replace(status === "authenticated" ? "/dashboard" : "/signup")
  }, [status, router])

  return (
    <div className="flex min-h-svh flex-1 items-center justify-center">
      <Loader2 className="size-6 animate-spin text-muted-foreground" aria-label="Loading" />
    </div>
  )
}
