"use client"

import { zodResolver } from "@hookform/resolvers/zod"
import { Loader2, MailCheck } from "lucide-react"
import { useRouter } from "next/navigation"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { InputOTP, InputOTPGroup, InputOTPSlot } from "@/components/ui/input-otp"
import { useCountdown } from "@/hooks/useCountdown"
import { ApiError } from "@/lib/api/errors"
import { getErrorMessage } from "@/lib/api/getErrorMessage"
import * as authApi from "@/lib/auth/authApi"
import { msFromNowSeconds } from "@/lib/time"
import { type ResetOtpFormValues, resetOtpSchema } from "@/lib/validation"

interface ResetOtpFormProps {
  email: string
  resendAt: number
}

export function ResetOtpForm({ email, resendAt }: ResetOtpFormProps) {
  const router = useRouter()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isResending, setIsResending] = useState(false)
  const [currentResendAt, setCurrentResendAt] = useState<number | null>(resendAt)
  const [lockedUntil, setLockedUntil] = useState<number | null>(null)

  const resendCountdown = useCountdown(currentResendAt)
  const lockCountdown = useCountdown(lockedUntil)
  const isLocked = lockedUntil !== null && lockCountdown > 0
  const canResend = !isResending && !isLocked && resendCountdown <= 0

  const form = useForm<ResetOtpFormValues>({
    resolver: zodResolver(resetOtpSchema),
    defaultValues: { otp: "" },
    mode: "onBlur",
  })

  async function onSubmit(values: ResetOtpFormValues) {
    setIsSubmitting(true)
    try {
      const response = await authApi.verifyResetPasswordOtp(email, values.otp)
      // Intermediate step, not a completed action -- matches the existing
      // no-toast pattern on login/signup's OTP hand-off (see docs/ui-ux-design.md).
      const params = new URLSearchParams({ reset_token: response.reset_token, email })
      router.push(`/reset-password/confirm?${params.toString()}`)
    } catch (err) {
      if (err instanceof ApiError && err.code === "ACCOUNT_LOCKED") {
        setLockedUntil(msFromNowSeconds(err.retryAfterSeconds ?? 900))
      }
      toast.error(getErrorMessage(err))
      form.resetField("otp")
      setIsSubmitting(false)
    }
  }

  async function handleResend() {
    if (!canResend) return
    setIsResending(true)
    try {
      const response = await authApi.forgotPassword(email)
      setCurrentResendAt(msFromNowSeconds(response.resend_cooldown_seconds))
      toast.success("A new code is on its way.")
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setIsResending(false)
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} noValidate className="space-y-6">
        <div className="flex items-center gap-2.5 rounded-lg border border-border bg-muted/40 px-3.5 py-3">
          <MailCheck className="size-4 shrink-0 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            Code sent to <span className="font-medium text-foreground">{email}</span>
          </p>
        </div>

        <FormField
          control={form.control}
          name="otp"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="text-[15px]">Verification code</FormLabel>
              <FormControl>
                <InputOTP maxLength={6} disabled={isSubmitting || isLocked} {...field}>
                  <InputOTPGroup>
                    {[0, 1, 2, 3, 4, 5].map((index) => (
                      <InputOTPSlot key={index} index={index} />
                    ))}
                  </InputOTPGroup>
                </InputOTP>
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {isLocked ? (
          <p aria-live="polite" className="text-center text-sm font-medium text-destructive">
            Too many attempts. Try again in {lockCountdown}s.
          </p>
        ) : null}

        <Button type="submit" className="h-12 w-full text-base" disabled={isSubmitting || isLocked}>
          {isSubmitting ? <Loader2 className="animate-spin" /> : null}
          Verify code
        </Button>

        <div className="flex flex-col items-center gap-1">
          <Button type="button" variant="link" disabled={!canResend} onClick={handleResend} className="h-auto text-sm">
            {isResending ? (
              <span className="inline-flex items-center gap-1.5">
                <Loader2 className="size-3.5 animate-spin" />
                Sending...
              </span>
            ) : resendCountdown > 0 && !isLocked ? (
              `Resend code in ${resendCountdown}s`
            ) : (
              "Resend code"
            )}
          </Button>
        </div>
      </form>
    </Form>
  )
}
