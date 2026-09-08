"use client"

import Link from "next/link"
import { useSearchParams } from "next/navigation"

import { AuthLayout } from "@/components/auth/AuthLayout"
import { NewPasswordForm } from "@/components/auth/NewPasswordForm"
import { Button } from "@/components/ui/button"

export function ResetPasswordConfirmClient() {
  const searchParams = useSearchParams()
  const resetToken = searchParams.get("reset_token")

  if (!resetToken) {
    return (
      <AuthLayout title="Reset session not found" description="This link is missing or no longer valid.">
        <Button render={<Link href="/forgot-password" />} size="lg" className="w-full">
          Start over
        </Button>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout title="Choose a new password" description="Create a strong new password for your account.">
      <NewPasswordForm resetToken={resetToken} />
    </AuthLayout>
  )
}
