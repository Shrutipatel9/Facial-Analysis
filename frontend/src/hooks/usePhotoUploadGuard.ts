"use client"

import { usePathname, useRouter } from "next/navigation"
import { useEffect, useRef } from "react"

import * as photoApi from "@/lib/photos/photoApi"
import { getNextOnboardingStep } from "@/lib/onboarding/nextStep"
import { useAnalysisStore } from "@/store/analysisStore"
import { usePaymentStore } from "@/store/paymentStore"
import { usePhotoStore } from "@/store/photoStore"

const PHOTOS_PATH = "/photos"

/**
 * Loads photo-set status and bounces a user who ALREADY had every angle
 * passed *before this page visit* away from its own page -- to whichever
 * step is actually next (getNextOnboardingStep), not hardcoded to
 * /dashboard, so a direct revisit to /photos doesn't cause a
 * second flash-then-redirect through /dashboard when analysis is also
 * still incomplete.
 *
 * Deliberately does NOT auto-redirect the instant the LAST angle passes
 * live during this visit (`completed` flipping false -> true while the
 * user is still on the page) -- PhotoWizard.tsx shows an explicit
 * "Continue" screen for that transition instead, so completing the set
 * doesn't yank the user away before they can see their own result. The
 * `wasCompletedOnFetch` ref captures the *initial* status fetch's answer
 * once, before any live upload this visit could change it, and that's the
 * only thing this effect's auto-redirect responds to.
 *
 * Does NOT redirect an incomplete user away from /dashboard itself --
 * that decision is centralized in useOnboardingEntryGuard
 * ((protected)/layout.tsx). See useQuestionnaireGuard's docstring for why
 * (a redirect race that could send a brand-new user anywhere in the chain).
 *
 * Only enabled once the questionnaire guard has already cleared (a user
 * can't sensibly reach /photos before finishing the questionnaire) -- see
 * (protected)/layout.tsx's wiring. That ordering guarantees the
 * questionnaire is complete by the time this guard's own redirect fires.
 */
export function usePhotoUploadGuard(enabled: boolean): { isChecking: boolean } {
  const completed = usePhotoStore((state) => state.completed)
  const setStatus = usePhotoStore((state) => state.setStatus)
  const paymentStatus = usePaymentStore((state) => state.status)
  const analysisStatus = useAnalysisStore((state) => state.status)
  const pathname = usePathname()
  const router = useRouter()
  const hasFetched = useRef(false)
  const wasCompletedOnFetch = useRef(false)

  useEffect(() => {
    if (!enabled || hasFetched.current) return
    hasFetched.current = true
    photoApi
      .getStatus()
      .then((status) => {
        wasCompletedOnFetch.current = status.completed
        setStatus(status)
      })
      .catch(() => {
        hasFetched.current = false
      })
  }, [enabled, setStatus])

  useEffect(() => {
    if (!completed || !wasCompletedOnFetch.current || pathname !== PHOTOS_PATH) return
    const target = getNextOnboardingStep({
      questionnaireCompleted: true,
      photosCompleted: true,
      paymentSucceeded: paymentStatus === "succeeded",
      analysisStatus: analysisStatus ?? "none",
    })
    router.replace(target)
  }, [completed, paymentStatus, analysisStatus, pathname, router])

  return { isChecking: enabled && completed === null }
}
