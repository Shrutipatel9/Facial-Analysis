"use client"

import { usePathname, useRouter } from "next/navigation"
import { useEffect } from "react"

import { getNextOnboardingStep, isPhotosIdentityOk } from "@/lib/onboarding/nextStep"
import { useAnalysisStore } from "@/store/analysisStore"
import { usePaymentStore } from "@/store/paymentStore"
import { usePhotoStore } from "@/store/photoStore"
import { useQuestionnaireStore } from "@/store/questionnaireStore"

/** Post-analysis home (`/home`), the interactive report (`/report`, also
 * only reachable once analysis is complete), and the legacy `/dashboard`
 * alias that now redirects to `/home`. */
const HOME_PATHS = new Set(["/home", "/report", "/dashboard"])

/**
 * Sends incomplete users away from the post-analysis home (`/home`, or the
 * legacy `/dashboard` alias) and the interactive report (`/report`). Waits
 * until questionnaire/photos/payment/analysis statuses are all known, then
 * picks one target via getNextOnboardingStep — one decision, not competing
 * redirects.
 *
 * getNextOnboardingStep's own "completed" target is always `/home` (the
 * single canonical next-step), but `/home` and `/report` are BOTH valid
 * once onboarding is actually complete -- `/report` is reached via nav/CTA
 * links, not a step in the funnel. So this only force-redirects when the
 * user isn't done yet (target is an earlier step); once target === "/home"
 * it leaves the user on whichever of /home or /report they're already on,
 * rather than bouncing /report back to /home on every visit.
 */
export function useOnboardingEntryGuard(enabled: boolean): void {
  const questionnaireCompleted = useQuestionnaireStore((state) => state.completed)
  const photosCompleted = usePhotoStore((state) => state.completed)
  const identityCheck = usePhotoStore((state) => state.identityCheck)
  const paymentStatus = usePaymentStore((state) => state.status)
  const analysisStatus = useAnalysisStore((state) => state.status)
  const pathname = usePathname()
  const router = useRouter()

  useEffect(() => {
    if (!enabled || !HOME_PATHS.has(pathname)) return
    if (
      questionnaireCompleted === null ||
      photosCompleted === null ||
      paymentStatus === null ||
      analysisStatus === null
    ) {
      return
    }

    const target = getNextOnboardingStep({
      questionnaireCompleted,
      photosCompleted,
      photosIdentityConsistent: isPhotosIdentityOk(photosCompleted, identityCheck),
      paymentSucceeded: paymentStatus === "succeeded",
      analysisStatus,
    })
    if (target !== "/home" && target !== pathname) {
      router.replace(target)
    }
  }, [
    enabled,
    pathname,
    questionnaireCompleted,
    photosCompleted,
    identityCheck,
    paymentStatus,
    analysisStatus,
    router,
  ])
}
