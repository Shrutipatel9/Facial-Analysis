"use client"

import { zodResolver } from "@hookform/resolvers/zod"
import { Loader2 } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { toast } from "sonner"

import { SettingsCard, SettingsSectionHeader } from "./settingsChrome"
import { Button } from "@/components/ui/button"
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { PasswordInput } from "@/components/ui/password-input"
import { ApiError } from "@/lib/api/errors"
import { getErrorMessage } from "@/lib/api/getErrorMessage"
import * as authApi from "@/lib/auth/authApi"
import { type ChangePasswordFormValues, changePasswordSchema } from "@/lib/validation"

/**
 * POST /auth/change-password -- deliberately does NOT sign the user out
 * (contrast the forgot-password OTP flow), since this is an authenticated
 * action proving identity via the current password itself. No ConfirmDialog
 * (BR-010): not destructive/irreversible.
 */
export function PasswordSection() {
  const [isSubmitting, setIsSubmitting] = useState(false)

  const form = useForm<ChangePasswordFormValues>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: { currentPassword: "", newPassword: "", confirmPassword: "" },
    mode: "onBlur",
  })

  async function onSubmit(values: ChangePasswordFormValues) {
    setIsSubmitting(true)
    try {
      await authApi.changePassword(values.currentPassword, values.newPassword)
      toast.success("Password changed.")
      form.reset()
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
  }

  return (
    <div className="w-full space-y-5">
      <SettingsSectionHeader title="Password" description="Change the password you use to sign in." />

      <SettingsCard>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} noValidate className="space-y-4">
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
      </SettingsCard>
    </div>
  )
}
