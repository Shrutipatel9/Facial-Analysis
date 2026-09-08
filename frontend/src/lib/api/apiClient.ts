/**
 * Thin re-exports so existing imports of `@/lib/api/apiClient` keep working.
 * All session/token logic lives in `authSession.ts`.
 */

export {
  authenticatedFormRequest,
  authenticatedRequest,
  checkBackendHealth,
  publicRequest,
  refreshSession as refreshAccessToken,
  type SessionTokens as RefreshResponse,
} from "@/lib/auth/authSession"
