import { z } from "zod"

// Mirrors Backend/app/services/password_service.py -- keep these two in
// sync if the rules ever change. Client-side validation is UX only; the
// backend re-validates and is the actual source of truth.
export const PASSWORD_MIN_LENGTH = 10
export const PASSWORD_MAX_LENGTH = 128

export const emailSchema = z.email("Enter a valid email address.")

/** Normalize the way the backend does (app/services/user_service.py) --
 * applied at submit time, not baked into the zod schema, since chaining
 * .trim()/.toLowerCase() after z.email() validates before those transforms
 * run rather than after. */
export function normalizeEmail(email: string): string {
  return email.trim().toLowerCase()
}

export const passwordSchema = z
  .string()
  .min(PASSWORD_MIN_LENGTH, `Password must be at least ${PASSWORD_MIN_LENGTH} characters.`)
  .max(PASSWORD_MAX_LENGTH, `Password must be at most ${PASSWORD_MAX_LENGTH} characters.`)
  .refine((value) => /[A-Za-z]/.test(value), "Password must contain at least one letter.")
  .refine((value) => /\d/.test(value), "Password must contain at least one number.")

export const signupSchema = z
  .object({
    email: emailSchema,
    password: passwordSchema,
  })
  .refine((data) => data.password.toLowerCase() !== normalizeEmail(data.email).split("@")[0], {
    message: "Password must not be the same as your email address.",
    path: ["password"],
  })

export type SignupFormValues = z.infer<typeof signupSchema>

export const loginSchema = z.object({
  email: emailSchema,
  password: z.string().min(1, "Enter your password."),
})

export type LoginFormValues = z.infer<typeof loginSchema>

export const otpSchema = z.object({
  otp: z
    .string()
    .length(6, "Enter the 6-digit code.")
    .regex(/^\d{6}$/, "Code must be 6 digits."),
})

export type OtpFormValues = z.infer<typeof otpSchema>

export const forgotPasswordSchema = z.object({
  email: emailSchema,
})

export type ForgotPasswordFormValues = z.infer<typeof forgotPasswordSchema>

export const resetPasswordSchema = z.object({
  otp: z
    .string()
    .length(6, "Enter the 6-digit code.")
    .regex(/^\d{6}$/, "Code must be 6 digits."),
  newPassword: passwordSchema,
})

export type ResetPasswordFormValues = z.infer<typeof resetPasswordSchema>

/** Scores 0-4, mirroring the backend's rules only (length, letter, digit) --
 * plus a couple of UX-only bonus signals (mixed case, symbol) that the
 * backend doesn't require but that make the meter feel less binary. */
export function scorePasswordStrength(password: string): 0 | 1 | 2 | 3 | 4 {
  if (!password) return 0
  let score = 0
  if (password.length >= PASSWORD_MIN_LENGTH) score++
  if (/[A-Za-z]/.test(password) && /\d/.test(password)) score++
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++
  if (/[^A-Za-z0-9]/.test(password) || password.length >= 16) score++
  return score as 0 | 1 | 2 | 3 | 4
}
