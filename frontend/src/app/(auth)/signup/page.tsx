import Link from "next/link"

import { AuthLayout } from "@/components/auth/AuthLayout"
import { SignupForm } from "@/components/auth/SignupForm"

export const metadata = {
  title: "Create account",
}

export default function SignupPage() {
  return (
    <AuthLayout
      title="Create your account"
      description="Get started with a free analysis."
      footer={
        <>
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-primary underline-offset-4 hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      <SignupForm />
    </AuthLayout>
  )
}
