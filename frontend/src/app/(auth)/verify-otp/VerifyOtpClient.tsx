"use client"

import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { toast } from "sonner"

import { AuthLayout } from "@/components/auth/AuthLayout"
import { OtpForm } from "@/components/auth/OtpForm"
import { Button } from "@/components/ui/button"
import { acceptAuthTokens, type Purpose, type TokenResponse } from "@/lib/auth/authApi"

function isPurpose(value: string | null): value is Purpose {
  return value === "signup" || value === "login"
}

export function VerifyOtpClient() {
  const router = useRouter()
  const searchParams = useSearchParams()

  const challengeId = searchParams.get("challenge_id")
  const purpose = searchParams.get("purpose")
  const email = searchParams.get("email")
  const expiresAt = Number(searchParams.get("expires_at"))
  const resendAt = Number(searchParams.get("resend_at"))

  const isValid =
    !!challengeId && isPurpose(purpose) && !!email && Number.isFinite(expiresAt) && Number.isFinite(resendAt)

  if (!isValid) {
    return (
      <AuthLayout title="Verification session not found" description="This link is missing or no longer valid.">
        <Button render={<Link href="/signup" />} size="lg" className="w-full">
          Start over
        </Button>
      </AuthLayout>
    )
  }

  function handleSuccess(tokens: TokenResponse) {
    acceptAuthTokens(tokens)
    toast.success("Welcome! You're all set.")
    router.replace("/dashboard")
  }

  return (
    <AuthLayout
      title="Verify your code"
      description={purpose === "signup" ? "One more step to activate your account." : "Confirm it's you to continue."}
    >
      <OtpForm
        challengeId={challengeId}
        email={email}
        expiresAt={expiresAt}
        resendAt={resendAt}
        onSuccess={handleSuccess}
      />
    </AuthLayout>
  )
}
