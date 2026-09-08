"use client"

import { Menu } from "@base-ui/react/menu"
import { ChevronDown, LogOut } from "lucide-react"
import { useRouter } from "next/navigation"
import { useState } from "react"
import { toast } from "sonner"

import { ConfirmDialog } from "@/components/ui/confirm-dialog"
import { getErrorMessage } from "@/lib/api/getErrorMessage"
import * as authApi from "@/lib/auth/authApi"
import { cn } from "@/lib/utils"
import { useAuthStore } from "@/store/authStore"

function userInitials(email: string | undefined): string {
  if (!email) return "?"
  const local = email.split("@")[0] ?? email
  const parts = local.split(/[._-]/).filter(Boolean)
  if (parts.length >= 2) {
    return `${parts[0]![0] ?? ""}${parts[1]![0] ?? ""}`.toUpperCase()
  }
  return local.slice(0, 2).toUpperCase()
}

/**
 * Corner account control: round initials + chevron so it reads as a menu.
 */
export function UserMenu() {
  const user = useAuthStore((state) => state.user)
  const router = useRouter()
  const [confirmOpen, setConfirmOpen] = useState(false)
  const initials = userInitials(user?.email)

  async function handleLogout() {
    try {
      await authApi.logout()
      toast.success("Signed out.")
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      router.replace("/login")
    }
  }

  return (
    <>
      <Menu.Root>
        <Menu.Trigger
          className={cn(
            "group flex cursor-pointer items-center gap-1.5 rounded-full border border-primary/15 bg-card/90 py-1 pr-2.5 pl-1 shadow-sm outline-none transition",
            "hover:border-primary/25 hover:bg-card hover:shadow-md",
            "focus-visible:ring-3 focus-visible:ring-ring/50",
            "data-popup-open:border-primary/30 data-popup-open:bg-card data-popup-open:shadow-md"
          )}
          aria-label="Account menu"
        >
          <span className="flex size-8 items-center justify-center rounded-full bg-primary text-[11px] font-semibold tracking-wide text-primary-foreground ring-2 ring-primary/10">
            {initials}
          </span>
          <ChevronDown className="size-3.5 text-primary/60 transition duration-200 group-data-popup-open:rotate-180 group-hover:text-primary" />
        </Menu.Trigger>

        <Menu.Portal>
          <Menu.Positioner side="bottom" align="end" sideOffset={8} className="z-50 outline-none">
            <Menu.Popup
              className={cn(
                "w-[17.5rem] origin-[var(--transform-origin)] overflow-hidden rounded-2xl border border-primary/10 bg-card text-card-foreground shadow-[0_16px_40px_-16px_rgba(20,55,75,0.32)] outline-none",
                "data-open:animate-in data-open:fade-in-0 data-open:zoom-in-95 data-closed:animate-out data-closed:fade-out-0 data-closed:zoom-out-95"
              )}
            >
              <div className="relative overflow-hidden px-4 pt-4 pb-3.5">
                <div
                  className="pointer-events-none absolute inset-0 bg-gradient-to-br from-primary/[0.08] via-transparent to-transparent"
                  aria-hidden
                />
                <div className="relative flex items-center gap-3">
                  <span className="flex size-11 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-semibold tracking-wide text-primary-foreground shadow-sm shadow-primary/25">
                    {initials}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-[11px] font-medium tracking-wide text-primary/70 uppercase">
                      Signed in as
                    </p>
                    <p className="mt-0.5 truncate text-sm font-medium leading-snug">{user?.email}</p>
                  </div>
                </div>
              </div>

              <div className="mx-3 border-t border-primary/10" />

              <div className="p-2">
                <Menu.Item
                  className={cn(
                    "flex w-full cursor-pointer items-center gap-2.5 rounded-xl px-2.5 py-2 text-sm outline-none transition",
                    "data-highlighted:bg-primary/[0.07] data-highlighted:text-foreground"
                  )}
                  onClick={() => setConfirmOpen(true)}
                >
                  <span className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <LogOut className="size-3.5" />
                  </span>
                  <span className="font-medium">Sign out</span>
                </Menu.Item>
              </div>
            </Menu.Popup>
          </Menu.Positioner>
        </Menu.Portal>
      </Menu.Root>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Sign out?"
        description="You'll need to log in again to continue."
        confirmLabel="Sign out"
        variant="default"
        icon={LogOut}
        onConfirm={handleLogout}
      />
    </>
  )
}
