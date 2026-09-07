"use client"

import { zodResolver } from "@hookform/resolvers/zod"
import { Loader2 } from "lucide-react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { PasswordInput } from "@/components/ui/password-input"
import { getErrorMessage } from "@/lib/api/getErrorMessage"
import * as authApi from "@/lib/auth/authApi"
import { buildVerifyOtpParams } from "@/lib/auth/challengeNav"
import { type LoginFormValues, loginSchema, normalizeEmail } from "@/lib/validation"

export function LoginForm() {
  const router = useRouter()
  const [isSubmitting, setIsSubmitting] = useState(false)

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
    mode: "onBlur",
  })

  async function onSubmit(values: LoginFormValues) {
    setIsSubmitting(true)
    try {
      const email = normalizeEmail(values.email)
      // Deliberately generic error copy on failure (see the catch block):
      // the backend already responds identically for "wrong password" and
      // "no such account" (anti-enumeration), and the UI must not
      // reintroduce specificity here.
      const challenge = await authApi.login(email, values.password)
      const params = buildVerifyOtpParams(challenge, email)
      router.push(`/verify-otp?${params.toString()}`)
    } catch (err) {
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

        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <div className="flex items-center justify-between">
                <FormLabel className="text-[15px]">Password</FormLabel>
                <Link
                  href="/forgot-password"
                  className="text-sm font-medium text-primary underline-offset-4 hover:underline"
                >
                  Forgot password?
                </Link>
              </div>
              <FormControl>
                <PasswordInput
                  className="h-12 text-base"
                  autoComplete="current-password"
                  placeholder="••••••••••"
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
          Sign in
        </Button>
      </form>
    </Form>
  )
}
