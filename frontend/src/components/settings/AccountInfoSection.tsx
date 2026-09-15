"use client"

import { Loader2 } from "lucide-react"
import { useEffect, useState } from "react"

import { SettingsCard, SettingsSectionHeader } from "./settingsChrome"
import { Badge } from "@/components/ui/badge"
import { getErrorMessage } from "@/lib/api/getErrorMessage"
import { formatDate } from "@/lib/format"
import * as userApi from "@/lib/users/userApi"
import type { UserProfile } from "@/lib/users/userApi"

/**
 * View-only -- DATA-001's only editable field is the password (see
 * PasswordSection); full_name is captured once at signup, not editable
 * here (client_requirements.md's ASM-009 history).
 */
export function AccountInfoSection() {
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    userApi
      .getMe()
      .then((data) => {
        if (!cancelled) setProfile(data)
      })
      .catch((err) => {
        if (!cancelled) setErrorMessage(getErrorMessage(err))
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="w-full space-y-5">
      <SettingsSectionHeader title="Account Info" description="Your account details." />

      <SettingsCard>
        {errorMessage ? (
          <p className="text-sm text-destructive">{errorMessage}</p>
        ) : profile === null ? (
          <div className="flex items-center justify-center py-10">
            <Loader2 className="size-5 animate-spin text-primary/50" aria-label="Loading" />
          </div>
        ) : (
          <dl className="divide-y divide-border/70">
            {profile.full_name ? (
              <div className="flex items-center justify-between gap-4 py-3.5 first:pt-0 last:pb-0">
                <dt className="shrink-0 text-sm text-muted-foreground">Name</dt>
                <dd className="truncate text-right text-sm font-medium text-foreground">{profile.full_name}</dd>
              </div>
            ) : null}
            <div className="flex items-center justify-between gap-4 py-3.5 first:pt-0 last:pb-0">
              <dt className="shrink-0 text-sm text-muted-foreground">Email</dt>
              <dd className="truncate text-right text-sm font-medium text-foreground">{profile.email}</dd>
            </div>
            <div className="flex items-center justify-between gap-4 py-3.5 first:pt-0 last:pb-0">
              <dt className="shrink-0 text-sm text-muted-foreground">Status</dt>
              <dd>
                <Badge variant={profile.verification_status === "verified" ? "default" : "secondary"}>
                  {profile.verification_status}
                </Badge>
              </dd>
            </div>
            <div className="flex items-center justify-between gap-4 py-3.5 first:pt-0 last:pb-0">
              <dt className="shrink-0 text-sm text-muted-foreground">Member since</dt>
              <dd className="text-right text-sm font-medium text-foreground">{formatDate(profile.created_at)}</dd>
            </div>
          </dl>
        )}
      </SettingsCard>
    </div>
  )
}
