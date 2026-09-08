"use client"

import Link from "next/link"
import { useSearchParams } from "next/navigation"

import { AuthLayout } from "@/components/auth/AuthLayout"
import { ResetOtpForm } from "@/components/auth/ResetOtpForm"
import { Button } from "@/components/ui/button"

export function ResetPasswordClient() {
  const searchParams = useSearchParams()

  const email = searchParams.get("email")
  const resendAt = Number(searchParams.get("resend_at"))

  const isValid = !!email && Number.isFinite(resendAt)

  if (!isValid) {
    return (
      <AuthLayout title="Reset session not found" description="This link is missing or no longer valid.">
        <Button render={<Link href="/forgot-password" />} nativeButton={false} size="lg" className="w-full">
          Start over
        </Button>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout title="Enter your reset code" description="Check your inbox for the 6-digit code we sent you.">
      <ResetOtpForm email={email} resendAt={resendAt} />
    </AuthLayout>
  )
}
