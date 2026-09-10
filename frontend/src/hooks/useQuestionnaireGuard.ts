"use client"

import { usePathname, useRouter } from "next/navigation"
import { useEffect, useRef } from "react"

import * as questionnaireApi from "@/lib/questionnaire/questionnaireApi"
import { getNextOnboardingStep, isPhotosIdentityOk } from "@/lib/onboarding/nextStep"
import { useAnalysisStore } from "@/store/analysisStore"
import { usePaymentStore } from "@/store/paymentStore"
import { usePhotoStore } from "@/store/photoStore"
import { useQuestionnaireStore } from "@/store/questionnaireStore"

const QUESTIONNAIRE_PATH = "/questionnaire"

/**
 * Loads questionnaire status and bounces a user who has ALREADY completed
 * it away from its own page -- to whichever step is actually next
 * (getNextOnboardingStep), not hardcoded to /dashboard, so a direct
 * revisit to /questionnaire doesn't cause a second flash-then-redirect
 * through /dashboard when photos/analysis are also still incomplete.
 *
 * Does NOT redirect an incomplete user away from /dashboard itself --
 * that decision is centralized in useOnboardingEntryGuard
 * ((protected)/layout.tsx), which waits for every step's status to be
 * known before picking one target. Each guard racing to call
 * router.replace() from the same stale /dashboard pathname the instant
 * its OWN fetch resolved (regardless of the other guards' fetches) used
 * to let whichever one resolved last silently win, sending a brand-new
 * user to an arbitrary step -- including straight to /analysis with
 * nothing completed. See useOnboardingEntryGuard's docstring.
 */
export function useQuestionnaireGuard(enabled: boolean): { isChecking: boolean } {
  const completed = useQuestionnaireStore((state) => state.completed)
  const setCompleted = useQuestionnaireStore((state) => state.setCompleted)
  const photosCompleted = usePhotoStore((state) => state.completed)
  const photosIdentityCheck = usePhotoStore((state) => state.identityCheck)
  const paymentStatus = usePaymentStore((state) => state.status)
  const analysisStatus = useAnalysisStore((state) => state.status)
  const pathname = usePathname()
  const router = useRouter()
  const hasFetched = useRef(false)

  useEffect(() => {
    if (!enabled || hasFetched.current) return
    hasFetched.current = true
    questionnaireApi
      .getStatus()
      .then((status) => setCompleted(status.completed))
      .catch(() => {
        hasFetched.current = false
      })
  }, [enabled, setCompleted])

  useEffect(() => {
    if (!completed || pathname !== QUESTIONNAIRE_PATH) return
    // photosCompleted/paymentStatus/analysisStatus may still be null this
    // early (their own guards haven't resolved yet) -- fall back to the
    // (harmless, rare) /dashboard relay in that case rather than blocking
    // the bounce.
    const target = getNextOnboardingStep({
      questionnaireCompleted: true,
      photosCompleted: photosCompleted ?? false,
      photosIdentityConsistent: isPhotosIdentityOk(photosCompleted, photosIdentityCheck),
      paymentSucceeded: paymentStatus === "succeeded",
      analysisStatus: analysisStatus ?? "none",
    })
    router.replace(target)
  }, [completed, photosCompleted, photosIdentityCheck, paymentStatus, analysisStatus, pathname, router])

  return { isChecking: enabled && completed === null }
}
