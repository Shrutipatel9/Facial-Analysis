import Link from "next/link"

import { AuthLayout } from "@/components/auth/AuthLayout"
import { LoginForm } from "@/components/auth/LoginForm"

export const metadata = {
  title: "Sign in",
}

export default function LoginPage() {
  return (
    <AuthLayout
      title="Welcome back"
      description="Sign in to continue to your account."
      footer={
        <>
          Don&apos;t have an account?{" "}
          <Link href="/signup" className="font-medium text-primary underline-offset-4 hover:underline">
            Create one
          </Link>
        </>
      }
    >
      <LoginForm />
    </AuthLayout>
  )
}
