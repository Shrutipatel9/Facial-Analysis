"use client"

import { zodResolver } from "@hookform/resolvers/zod"
import { KeyRound, Loader2, UserRound } from "lucide-react"
import { useEffect, useState } from "react"
import { useForm } from "react-hook-form"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { PasswordInput } from "@/components/ui/password-input"
import { ApiError } from "@/lib/api/errors"
import { getErrorMessage } from "@/lib/api/getErrorMessage"
import * as authApi from "@/lib/auth/authApi"
import { formatDate } from "@/lib/format"
import * as userApi from "@/lib/users/userApi"
import type { UserProfile } from "@/lib/users/userApi"
import { type ChangePasswordFormValues, changePasswordSchema } from "@/lib/validation"

/**
 * View-only for email/name/status -- DATA-001's only editable field is the
 * password (full_name is captured once at signup, not editable here; see
 * client_requirements.md's ASM-009 history). Password change is an inline
 * form (current + new + confirm), submitted to POST /auth/change-password
 * -- deliberately does NOT sign the user out (contrast the forgot-password
 * OTP flow), since this is an authenticated action proving identity via
 * the current password itself.
 */
export function ProfileCard() {
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isChangingPassword, setIsChangingPassword] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const form = useForm<ChangePasswordFormValues>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: { currentPassword: "", newPassword: "", confirmPassword: "" },
    mode: "onBlur",
  })

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

  async function onSubmit(values: ChangePasswordFormValues) {
    setIsSubmitting(true)
    try {
      await authApi.changePassword(values.currentPassword, values.newPassword)
      toast.success("Password changed.")
      form.reset()
      setIsChangingPassword(false)
    } catch (err) {
      if (err instanceof ApiError && err.code === "CURRENT_PASSWORD_INCORRECT") {
        form.setError("currentPassword", { message: err.message })
      } else {
        toast.error(getErrorMessage(err))
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  function handleCancel() {
    form.reset()
    setIsChangingPassword(false)
  }

  return (
    <div className="flex h-full flex-col gap-4 rounded-2xl border border-border/80 bg-card p-6 shadow-[0_10px_30px_-18px_rgba(20,55,75,0.28)]">
      <div className="flex items-center gap-2.5">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
          <UserRound className="size-4" />
        </span>
        <h2 className="font-heading text-lg font-semibold tracking-tight">Profile</h2>
      </div>

      {errorMessage ? (
        <p className="text-sm text-destructive">{errorMessage}</p>
      ) : profile === null ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="size-5 animate-spin text-primary/50" aria-label="Loading" />
        </div>
      ) : (
        <div className="space-y-4">
          <div className="space-y-2 text-sm">
            {profile.full_name ? (
              <div className="flex items-center justify-between gap-2">
                <span className="text-muted-foreground">Name</span>
                <span className="truncate font-medium">{profile.full_name}</span>
              </div>
            ) : null}
            <div className="flex items-center justify-between gap-2">
              <span className="text-muted-foreground">Email</span>
              <span className="truncate font-medium">{profile.email}</span>
            </div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-muted-foreground">Status</span>
              <Badge variant={profile.verification_status === "verified" ? "default" : "secondary"}>
                {profile.verification_status}
              </Badge>
            </div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-muted-foreground">Member since</span>
              <span className="font-medium">{formatDate(profile.created_at)}</span>
            </div>
          </div>

          {isChangingPassword ? (
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} noValidate className="space-y-3 border-t border-border pt-4">
                <FormField
                  control={form.control}
                  name="currentPassword"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm">Current password</FormLabel>
                      <FormControl>
                        <PasswordInput autoComplete="current-password" disabled={isSubmitting} {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="newPassword"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm">New password</FormLabel>
                      <FormControl>
                        <PasswordInput
                          autoComplete="new-password"
                          placeholder="At least 10 characters"
                          disabled={isSubmitting}
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="confirmPassword"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm">Confirm new password</FormLabel>
                      <FormControl>
                        <PasswordInput autoComplete="new-password" disabled={isSubmitting} {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <div className="flex gap-2.5 pt-1">
                  <Button
                    type="button"
                    variant="outline"
                    className="h-10 flex-1 rounded-full"
                    onClick={handleCancel}
                    disabled={isSubmitting}
                  >
                    Cancel
                  </Button>
                  <Button type="submit" className="h-10 flex-1 rounded-full" disabled={isSubmitting}>
                    {isSubmitting ? <Loader2 className="size-4 animate-spin" /> : null}
                    Save
                  </Button>
                </div>
              </form>
            </Form>
          ) : (
            <Button
              variant="outline"
              className="h-10 w-full rounded-full"
              onClick={() => setIsChangingPassword(true)}
            >
              <KeyRound className="size-4" />
              Change password
            </Button>
          )}
        </div>
      )}
    </div>
  )
}
