import Link from "next/link"

import { AuthLayout } from "@/components/auth/AuthLayout"
import { ForgotPasswordForm } from "@/components/auth/ForgotPasswordForm"

export const metadata = {
  title: "Forgot password",
}

export default function ForgotPasswordPage() {
  return (
    <AuthLayout
      title="Forgot your password?"
      description="Enter your email and we'll send you a code to reset it."
      footer={
        <>
          Remembered it?{" "}
          <Link href="/login" className="font-medium text-primary underline-offset-4 hover:underline">
            Back to sign in
          </Link>
        </>
      }
    >
      <ForgotPasswordForm />
    </AuthLayout>
  )
}
