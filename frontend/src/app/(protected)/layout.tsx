"use client"

import { Loader2, LogOut } from "lucide-react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { ConfirmDialog } from "@/components/ui/confirm-dialog"
import { useAuthGuard } from "@/hooks/useAuthGuard"
import { getErrorMessage } from "@/lib/api/getErrorMessage"
import * as authApi from "@/lib/auth/authApi"
import { useAuthStore } from "@/store/authStore"

export default function ProtectedRouteGroupLayout({ children }: { children: React.ReactNode }) {
  const { isChecking } = useAuthGuard()
  const user = useAuthStore((state) => state.user)
  const router = useRouter()

  async function handleLogout() {
    try {
      await authApi.logout()
      toast.success("Signed out.")
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      // logoutSession always clears Zustand locally; always leave protected routes.
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
            <ConfirmDialog
              trigger={
                <Button variant="outline" size="sm">
                  <LogOut />
                  Sign out
                </Button>
              }
              title="Sign out?"
              description="You'll need to log in again to continue."
              confirmLabel="Sign out"
              variant="default"
              icon={LogOut}
              onConfirm={handleLogout}
            />
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-10">{children}</main>
    </div>
  )
}
