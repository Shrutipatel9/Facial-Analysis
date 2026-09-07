"use client"

import { zodResolver } from "@hookform/resolvers/zod"
import { Loader2 } from "lucide-react"
import { useRouter } from "next/navigation"
import { useState } from "react"
import { useForm, useWatch } from "react-hook-form"
import { toast } from "sonner"

import { PasswordStrengthMeter } from "@/components/auth/PasswordStrengthMeter"
import { Button } from "@/components/ui/button"
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { PasswordInput } from "@/components/ui/password-input"
import { getErrorMessage } from "@/lib/api/getErrorMessage"
import * as authApi from "@/lib/auth/authApi"
import { buildVerifyOtpParams } from "@/lib/auth/challengeNav"
import { normalizeEmail, type SignupFormValues, signupSchema } from "@/lib/validation"

export function SignupForm() {
  const router = useRouter()
  const [isSubmitting, setIsSubmitting] = useState(false)

  const form = useForm<SignupFormValues>({
    resolver: zodResolver(signupSchema),
    defaultValues: { email: "", password: "" },
    mode: "onBlur",
  })

  const password = useWatch({ control: form.control, name: "password" })

  async function onSubmit(values: SignupFormValues) {
    setIsSubmitting(true)
    try {
      const email = normalizeEmail(values.email)
      const challenge = await authApi.register(email, values.password)
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
              <FormLabel className="text-[15px]">Password</FormLabel>
              <FormControl>
                <PasswordInput
                  className="h-12 text-base"
                  autoComplete="new-password"
                  placeholder="At least 10 characters"
                  disabled={isSubmitting}
                  {...field}
                />
              </FormControl>
              <PasswordStrengthMeter password={password} />
              <FormMessage />
            </FormItem>
          )}
        />

        <Button type="submit" className="h-12 w-full text-base" disabled={isSubmitting}>
          {isSubmitting ? <Loader2 className="animate-spin" /> : null}
          Create account
        </Button>
      </form>
    </Form>
  )
}
