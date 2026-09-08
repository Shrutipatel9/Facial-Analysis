"use client"

import { zodResolver } from "@hookform/resolvers/zod"
import { Loader2 } from "lucide-react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { useState } from "react"
import { useForm, useWatch } from "react-hook-form"
import { toast } from "sonner"

import { PasswordStrengthMeter } from "@/components/auth/PasswordStrengthMeter"
import { Button } from "@/components/ui/button"
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { PasswordInput } from "@/components/ui/password-input"
import { ApiError } from "@/lib/api/errors"
import { getErrorMessage } from "@/lib/api/getErrorMessage"
import * as authApi from "@/lib/auth/authApi"
import { type NewPasswordFormValues, newPasswordSchema } from "@/lib/validation"

interface NewPasswordFormProps {
  resetToken: string
}

export function NewPasswordForm({ resetToken }: NewPasswordFormProps) {
  const router = useRouter()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [tokenInvalid, setTokenInvalid] = useState(false)

  const form = useForm<NewPasswordFormValues>({
    resolver: zodResolver(newPasswordSchema),
    defaultValues: { newPassword: "", confirmPassword: "" },
    mode: "onBlur",
  })

  const newPassword = useWatch({ control: form.control, name: "newPassword" })

  async function onSubmit(values: NewPasswordFormValues) {
    setIsSubmitting(true)
    try {
      await authApi.resetPassword(resetToken, values.newPassword)
      toast.success("Password reset. Please log in with your new password.")
      router.push("/login")
    } catch (err) {
      if (err instanceof ApiError && err.code === "RESET_TOKEN_INVALID") {
        setTokenInvalid(true)
        return
      }
      toast.error(getErrorMessage(err))
      setIsSubmitting(false)
    }
  }

  if (tokenInvalid) {
    return (
      <div className="space-y-6 text-center">
        <p className="text-sm text-muted-foreground">
          This reset link is invalid or has expired. Please request a new one.
        </p>
        <Button render={<Link href="/forgot-password" />} size="lg" className="w-full">
          Start over
        </Button>
      </div>
    )
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} noValidate className="space-y-6">
        <FormField
          control={form.control}
          name="newPassword"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="text-[15px]">New password</FormLabel>
              <FormControl>
                <PasswordInput
                  className="h-12 text-base"
                  autoComplete="new-password"
                  placeholder="At least 10 characters"
                  disabled={isSubmitting}
                  {...field}
                />
              </FormControl>
              <PasswordStrengthMeter password={newPassword} />
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="confirmPassword"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="text-[15px]">Confirm new password</FormLabel>
              <FormControl>
                <PasswordInput
                  className="h-12 text-base"
                  autoComplete="new-password"
                  placeholder="Re-enter your new password"
                  disabled={isSubmitting}
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <Button type="submit" className="h-12 w-full text-base" disabled={isSubmitting}>
          {isSubmitting ? <Loader2 className="animate-spin" /> : null}
          Confirm
        </Button>
      </form>
    </Form>
  )
}
