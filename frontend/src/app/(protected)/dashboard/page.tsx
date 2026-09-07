"use client"

import { CheckCircle2 } from "lucide-react"

import { useAuthStore } from "@/store/authStore"

export default function DashboardPage() {
  const user = useAuthStore((state) => state.user)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Welcome{user ? `, ${user.email}` : ""}</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Authentication is wired up. The onboarding questionnaire, photo upload, and report modules land in later
          phases.
        </p>
      </div>

      <div className="flex items-start gap-3 rounded-lg border border-border bg-card p-4">
        <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-success" />
        <div className="space-y-1 text-sm">
          <p className="font-medium">You&apos;re signed in</p>
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-muted-foreground">
            <dt>Role</dt>
            <dd>{user?.role}</dd>
            <dt>Verification</dt>
            <dd>{user?.verification_status}</dd>
          </dl>
        </div>
      </div>
    </div>
  )
}
