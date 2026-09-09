import type { AnalysisStatus } from "@/lib/analysis/analysisApi"

export type OnboardingPath = "/questionnaire" | "/photos" | "/payment" | "/analysis" | "/dashboard"

/**
 * The single source of truth for "where does this user belong right now,"
 * shared by every guard/completion handler that needs it
 * (useOnboardingEntryGuard, useQuestionnaireGuard, usePhotoUploadGuard,
 * usePaymentGuard) so the priority order is defined exactly once, not
 * re-implemented per call site.
 *
 * Payment sits between photos and analysis (FR-015, BR-001) -- analysis
 * cannot even be triggered until payment succeeds
 * (Backend/app/services/analysis_service.py's trigger_analysis), so a user
 * who hasn't paid yet must never reach /analysis at all, not even to see a
 * "processing" state.
 *
 * Completing a step should navigate DIRECTLY to this function's result,
 * never to /dashboard as a relay -- routing through /dashboard first (even
 * though (protected)/layout.tsx's guards would immediately bounce an
 * incomplete user onward) renders the actual dashboard page content for
 * one frame before the redirect effect fires, since by the time an earlier
 * step completes, the later guards have typically already resolved their
 * own status fetches in the background and stopped gating the loader.
 */
export function getNextOnboardingStep(params: {
  questionnaireCompleted: boolean
  photosCompleted: boolean
  paymentSucceeded: boolean
  analysisStatus: AnalysisStatus
}): OnboardingPath {
  if (!params.questionnaireCompleted) return "/questionnaire"
  if (!params.photosCompleted) return "/photos"
  if (!params.paymentSucceeded) return "/payment"
  if (params.analysisStatus !== "completed") return "/analysis"
  return "/dashboard"
}
