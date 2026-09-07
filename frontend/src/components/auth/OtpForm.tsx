"use client"

import { Loader2, MailCheck } from "lucide-react"
import { motion } from "motion/react"
import { type FormEvent, useState } from "react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { InputOTP, InputOTPGroup, InputOTPSlot } from "@/components/ui/input-otp"
import { useCountdown } from "@/hooks/useCountdown"
import { ApiError } from "@/lib/api/errors"
import { getErrorMessage } from "@/lib/api/getErrorMessage"
import * as authApi from "@/lib/auth/authApi"
import type { TokenResponse } from "@/lib/auth/authApi"
import { msFromNowSeconds, pastTimestamp } from "@/lib/time"

interface OtpFormProps {
  challengeId: string
  email: string
  expiresAt: number
  resendAt: number
  onSuccess: (tokens: TokenResponse) => void
}

const OTP_LENGTH = 6

function formatSeconds(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return minutes > 0 ? `${minutes}:${String(seconds).padStart(2, "0")}` : `${seconds}s`
}

export function OtpForm({ challengeId, email, expiresAt, resendAt, onSuccess }: OtpFormProps) {
  const [currentChallengeId, setCurrentChallengeId] = useState(challengeId)
  const [currentExpiresAt, setCurrentExpiresAt] = useState(expiresAt)
  const [currentResendAt, setCurrentResendAt] = useState(resendAt)
  const [lockedUntil, setLockedUntil] = useState<number | null>(null)

  const [otp, setOtp] = useState("")
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isVerifying, setIsVerifying] = useState(false)
  const [isResending, setIsResending] = useState(false)

  const expirySeconds = useCountdown(currentExpiresAt)
  const resendCountdown = useCountdown(currentResendAt)
  const lockCountdown = useCountdown(lockedUntil)

  const isLocked = lockedUntil !== null && lockCountdown > 0
  const isExpired = !isLocked && expirySeconds <= 0
  const canResend = !isResending && !isLocked && resendCountdown <= 0
  const inputsDisabled = isVerifying || isLocked || isExpired
  const canVerify = otp.length === OTP_LENGTH && !inputsDisabled

  // Deliberately NOT wired to InputOTP's onComplete -- verification only
  // happens when the user explicitly submits (button click or Enter), never
  // just from typing the 6th digit.
  async function handleVerify(event: FormEvent) {
    event.preventDefault()
    if (!canVerify) return

    setIsVerifying(true)
    setErrorMessage(null)
    try {
      const tokens = await authApi.verifyOtp(currentChallengeId, otp)
      onSuccess(tokens)
      return
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.code === "ACCOUNT_LOCKED") {
          setLockedUntil(msFromNowSeconds(err.retryAfterSeconds ?? 900))
        } else if (err.code === "OTP_EXPIRED") {
          setCurrentExpiresAt(pastTimestamp())
        }
      }
      setErrorMessage(getErrorMessage(err))
      setOtp("")
    } finally {
      setIsVerifying(false)
    }
  }

  async function handleResend() {
    if (!canResend) return
    setIsResending(true)
    setErrorMessage(null)
    try {
      const challenge = await authApi.resendOtp(currentChallengeId)
      setCurrentChallengeId(challenge.challenge_id)
      setCurrentExpiresAt(msFromNowSeconds(challenge.otp_expiry_seconds))
      setCurrentResendAt(msFromNowSeconds(challenge.resend_cooldown_seconds))
      setOtp("")
      toast.success("A new code is on its way.")
    } catch (err) {
      if (err instanceof ApiError && err.code === "ACCOUNT_LOCKED") {
        setLockedUntil(msFromNowSeconds(err.retryAfterSeconds ?? 900))
      }
      setErrorMessage(getErrorMessage(err))
    } finally {
      setIsResending(false)
    }
  }

  return (
    <form onSubmit={handleVerify} noValidate className="space-y-6">
      <div className="flex items-center gap-2.5 rounded-lg border border-border bg-muted/40 px-3.5 py-3">
        <MailCheck className="size-4 shrink-0 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">
          Code sent to <span className="font-medium text-foreground">{email}</span>
        </p>
      </div>

      <div className="flex flex-col items-center gap-3">
        <InputOTP
          maxLength={OTP_LENGTH}
          value={otp}
          onChange={setOtp}
          disabled={inputsDisabled}
          aria-invalid={errorMessage ? true : undefined}
        >
          <InputOTPGroup>
            {[0, 1, 2, 3, 4, 5].map((index) => (
              <InputOTPSlot key={index} index={index} />
            ))}
          </InputOTPGroup>
        </InputOTP>
      </div>

      {/* Single status region: countdown / lockout / error state, in that
          priority order -- aria-live so screen-reader users hear state
          changes (lockout, expiry) without needing to re-focus the form. */}
      <div aria-live="polite" className="min-h-6 text-center text-base">
        {isLocked ? (
          <p className="font-medium text-destructive">Too many attempts. Try again in {formatSeconds(lockCountdown)}.</p>
        ) : errorMessage ? (
          <p className="text-destructive">{errorMessage}</p>
        ) : isExpired ? (
          <p className="text-muted-foreground">This code has expired.</p>
        ) : (
          <p className="text-muted-foreground">Code expires in {formatSeconds(expirySeconds)}</p>
        )}
      </div>

      <Button type="submit" className="h-12 w-full text-base" disabled={!canVerify}>
        {isVerifying ? <Loader2 className="animate-spin" /> : null}
        Verify code
      </Button>

      <div className="flex flex-col items-center gap-1">
        <Button
          type="button"
          variant="link"
          disabled={!canResend}
          onClick={handleResend}
          className="h-auto text-sm"
        >
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

      {isExpired ? (
        <motion.div initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }}>
          <Button
            type="button"
            variant="secondary"
            className="h-12 w-full text-base"
            onClick={handleResend}
            disabled={!canResend}
          >
            {isResending ? <Loader2 className="animate-spin" /> : null}
            Send a new code
          </Button>
        </motion.div>
      ) : null}
    </form>
  )
}
