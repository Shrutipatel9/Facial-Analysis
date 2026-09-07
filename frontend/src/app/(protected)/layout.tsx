"use client"

import { Loader2, LogOut } from "lucide-react"
import { useRouter } from "next/navigation"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import { useAuthGuard } from "@/hooks/useAuthGuard"
import * as authApi from "@/lib/auth/authApi"
import { useAuthStore } from "@/store/authStore"

export default function ProtectedRouteGroupLayout({ children }: { children: React.ReactNode }) {
  const { isChecking } = useAuthGuard()
  const user = useAuthStore((state) => state.user)
  const router = useRouter()
  const [isLoggingOut, setIsLoggingOut] = useState(false)

  async function handleLogout() {
    setIsLoggingOut(true)
    try {
      await authApi.logout()
    } finally {
      // logoutSession already cleared Zustand; always leave protected routes.
      router.replace("/login")
    }
  }

  if (isChecking) {
    return (
      <div className="flex min-h-svh items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" aria-label="Loading" />
      </div>
    )
  }

  return (
    <div className="min-h-svh">
      <header className="border-b border-border">
        <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-6">
          <span className="text-sm font-semibold tracking-tight">Facial Analysis</span>
          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-muted-foreground sm:inline">{user?.email}</span>
            <Button variant="outline" size="sm" onClick={handleLogout} disabled={isLoggingOut}>
              {isLoggingOut ? <Loader2 className="animate-spin" /> : <LogOut />}
              Sign out
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-10">{children}</main>
    </div>
  )
}
