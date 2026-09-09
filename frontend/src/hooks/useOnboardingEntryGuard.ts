"use client"

import { usePathname, useRouter } from "next/navigation"
import { useEffect } from "react"

import { getNextOnboardingStep } from "@/lib/onboarding/nextStep"
import { useAnalysisStore } from "@/store/analysisStore"
import { usePaymentStore } from "@/store/paymentStore"
import { usePhotoStore } from "@/store/photoStore"
import { useQuestionnaireStore } from "@/store/questionnaireStore"

const DASHBOARD_PATH = "/dashboard"

/**
 * The single place that decides where an incomplete user gets sent from
 * /dashboard. Each individual step guard (useQuestionnaireGuard,
 * usePhotoUploadGuard, useAnalysisGuard) only fetches its own status now
 * and bounces a user away from its OWN page once already complete --
 * none of them redirect away from /dashboard anymore.
 *
 * That used to be split across three independent effects, each calling
 * router.replace() the instant its own status fetch resolved, regardless
 * of whether the other two had resolved yet -- three redirects racing off
 * the same stale /dashboard pathname, with whichever resolved LAST
 * silently winning. A brand-new user with nothing completed could land on
 * /questionnaire, /photos, or /analysis depending on network timing
 * jitter alone (verified empirically: a fresh signup landed straight on
 * /analysis with zero questionnaire responses, zero photos, and zero
 * analysis results in the database).
 *
 * This hook waits until all three statuses are known, then picks exactly
 * one target via the shared getNextOnboardingStep priority order -- one
 * redirect decision, not three competing ones. It only matters for a
 * DIRECT visit to /dashboard (typed URL, bookmark, logo click, or a full
 * page reload while incomplete) -- completing a step navigates straight
 * to its own next step and never routes through /dashboard as a relay,
 * see getNextOnboardingStep's docstring.
 */
export function useOnboardingEntryGuard(enabled: boolean): void {
  const questionnaireCompleted = useQuestionnaireStore((state) => state.completed)
  const photosCompleted = usePhotoStore((state) => state.completed)
  const paymentStatus = usePaymentStore((state) => state.status)
  const analysisStatus = useAnalysisStore((state) => state.status)
  const pathname = usePathname()
  const router = useRouter()

  useEffect(() => {
    if (!enabled || pathname !== DASHBOARD_PATH) return
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
      paymentSucceeded: paymentStatus === "succeeded",
      analysisStatus,
    })
    if (target !== DASHBOARD_PATH) {
      router.replace(target)
    }
  }, [enabled, pathname, questionnaireCompleted, photosCompleted, paymentStatus, analysisStatus, router])
}
