import type { ChallengeResponse } from "./authApi"

/**
 * Builds the query params SignupForm/LoginForm hand off to /verify-otp.
 * Pulled out of both components (rather than duplicated inline) so the
 * Date.now()-based absolute-timestamp computation lives in a plain utility
 * module instead of a component body -- React Compiler's purity analysis
 * flags impure calls like Date.now() inside components/hooks even when
 * they're only reached from an event handler.
 */
export function buildVerifyOtpParams(challenge: ChallengeResponse, email: string): URLSearchParams {
  const now = Date.now()
  return new URLSearchParams({
    challenge_id: challenge.challenge_id,
    purpose: challenge.purpose,
    email,
    expires_at: String(now + challenge.otp_expiry_seconds * 1000),
    resend_at: String(now + challenge.resend_cooldown_seconds * 1000),
  })
}
