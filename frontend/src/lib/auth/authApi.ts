import {
  authenticatedRequest,
  establishSession,
  logoutSession,
  publicRequest,
  refreshSession,
  type SessionTokens,
} from "@/lib/auth/authSession"
import type { AuthUser } from "@/store/authStore"

export type Purpose = "signup" | "login"

export interface ChallengeResponse {
  challenge_id: string
  purpose: Purpose
  otp_expiry_seconds: number
  resend_cooldown_seconds: number
}

/** OTP verify success — access token + user in JSON; refresh cookie set by backend. */
export type TokenResponse = SessionTokens

export type RefreshResponse = SessionTokens

export interface MessageResponse {
  message: string
}

export interface ForgotPasswordResponse {
  message: string
  otp_expiry_seconds: number
  resend_cooldown_seconds: number
}

export function register(email: string, password: string): Promise<ChallengeResponse> {
  return publicRequest<ChallengeResponse>("/auth/register", { email, password })
}

export function login(email: string, password: string): Promise<ChallengeResponse> {
  return publicRequest<ChallengeResponse>("/auth/login", { email, password })
}

export function verifyOtp(challengeId: string, otp: string): Promise<TokenResponse> {
  return publicRequest<TokenResponse>("/auth/otp/verify", { challenge_id: challengeId, otp })
}

export function resendOtp(challengeId: string): Promise<ChallengeResponse> {
  return publicRequest<ChallengeResponse>("/auth/otp/resend", { challenge_id: challengeId })
}

/** Cookie-only refresh — prefer authSession.refreshSession / bootstrapSession. */
export function refreshTokens(): Promise<RefreshResponse> {
  return refreshSession()
}

export function getMe(): Promise<AuthUser> {
  return authenticatedRequest<AuthUser>("/auth/me", { method: "GET" })
}

export function forgotPassword(email: string): Promise<ForgotPasswordResponse> {
  return publicRequest<ForgotPasswordResponse>("/auth/forgot-password", { email })
}

export function resetPassword(email: string, otp: string, newPassword: string): Promise<MessageResponse> {
  return publicRequest<MessageResponse>("/auth/reset-password", {
    email,
    otp,
    new_password: newPassword,
  })
}

export function logout(): Promise<void> {
  return logoutSession()
}

/** Apply OTP-verify tokens into Zustand (cookie already set by that response). */
export function acceptAuthTokens(tokens: TokenResponse): void {
  establishSession(tokens)
}
