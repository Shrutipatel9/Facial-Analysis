"use client"

import { zodResolver } from "@hookform/resolvers/zod"
import { Loader2 } from "lucide-react"
import { useRouter } from "next/navigation"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { getErrorMessage } from "@/lib/api/getErrorMessage"
import * as authApi from "@/lib/auth/authApi"
import { msFromNowSeconds } from "@/lib/time"
import { type ForgotPasswordFormValues, forgotPasswordSchema, normalizeEmail } from "@/lib/validation"

export function ForgotPasswordForm() {
  const router = useRouter()
  const [isSubmitting, setIsSubmitting] = useState(false)

  const form = useForm<ForgotPasswordFormValues>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: "" },
    mode: "onBlur",
  })

  async function onSubmit(values: ForgotPasswordFormValues) {
    setIsSubmitting(true)
    try {
      const email = normalizeEmail(values.email)
      // Always succeeds with the same generic response whether or not the
      // account exists (see authApi.forgotPassword) -- so we always
      // advance to the reset-code screen, never branch on the result.
      const response = await authApi.forgotPassword(email)
      const params = new URLSearchParams({
        email,
        resend_at: String(msFromNowSeconds(response.resend_cooldown_seconds)),
      })
      router.push(`/reset-password?${params.toString()}`)
    } catch (err) {
      // Only reachable for genuine failures (network/rate-limit) -- account
      // existence never surfaces here.
      toast.error(getErrorMessage(err))
      setIsSubmitting(false)
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} noValidate className="space-y-6">
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="text-[15px]">Email</FormLabel>
              <FormControl>
                <Input
                  className="h-12 text-base"
                  type="email"
                  autoComplete="email"
                  placeholder="you@example.com"
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
          Send reset code
        </Button>
      </form>
    </Form>
  )
}
