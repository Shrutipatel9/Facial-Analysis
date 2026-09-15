import type { AnalysisStatus } from "@/lib/analysis/analysisApi"

export type OnboardingPath = "/questionnaire" | "/photos" | "/payment" | "/analysis" | "/home"

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
 * never through a relay route. Post-analysis home is `/home` (Home
 * Overview — the MyFace reference's own post-approval landing screen, see
 * docs/milestone2_home_and_report_spec.md §0/§1), not `/report` directly
 * and not a separate Welcome dashboard. `/report`'s interactive TOC stays
 * reachable from Home Overview's own "View Full Report" CTA and the
 * persistent header's "Report" nav item.
 *
 * `photosIdentityConsistent` (added alongside the cross-photo identity
 * check -- see photoStore.ts's `identityCheck`) is deliberately a
 * SEPARATE param from `photosCompleted`, not folded into it: every
 * required angle can individually pass BR-005's per-photo checks
 * (`photosCompleted: true`) while still not being the same person across
 * all three. Without this, a mismatched set sailed straight through to
 * /payment from any entry point that computes "what's next".
 * Pass `true` when photos are not complete yet (nothing to compare).
 * Once the set is complete, only an explicit `identityCheck.consistent
 * === true` counts — `null` means "still checking / unknown" after a
 * retake and must keep the user on /photos (see `isPhotosIdentityOk`).
 */
export function isPhotosIdentityOk(
  photosCompleted: boolean | null | undefined,
  identityCheck: { consistent: boolean } | null | undefined
): boolean {
  if (!photosCompleted) return true
  return identityCheck?.consistent === true
}

export function getNextOnboardingStep(params: {
  questionnaireCompleted: boolean
  photosCompleted: boolean
  photosIdentityConsistent: boolean
  paymentSucceeded: boolean
  analysisStatus: AnalysisStatus
}): OnboardingPath {
  if (!params.questionnaireCompleted) return "/questionnaire"
  if (!params.photosCompleted || !params.photosIdentityConsistent) return "/photos"
  if (!params.paymentSucceeded) return "/payment"
  if (params.analysisStatus !== "completed") return "/analysis"
  return "/home"
}
