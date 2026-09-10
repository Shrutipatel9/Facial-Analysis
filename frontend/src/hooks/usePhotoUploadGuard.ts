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
 *
 * Also does NOT auto-redirect when the cross-photo identity_check came
 * back inconsistent, even if `completed` was already true on the initial
 * fetch -- otherwise a user who left right as their 3rd photo passed
 * (before ever seeing PhotoSetCompleteStep's error banner) would get
 * silently bounced straight to payment/analysis on their next visit,
 * completely bypassing the one screen that shows and lets them fix a
 * mismatched photo. `is_photo_set_ready`/`completed` deliberately stay
 * true either way (every photo still individually passed BR-005) -- this
 * guard is the one place that additionally checks identity before
 * treating the set as "done, move on."
 *
 * `wasConsistentOnFetch` is captured ONCE, from that same initial fetch,
 * and is what the redirect below actually reads -- never the live,
 * reactive `identityCheck` from the store. That distinction matters: any
 * retake during this visit runs through photoStore.setAnglePhoto(), which
 * optimistically resets `identityCheck` to `null` the instant the upload
 * response comes back, *before* the fresh cross-photo re-check has even
 * started (see PhotoWizard.tsx's handleSubmitAngle). A `null` identityCheck
 * genuinely means "unknown, pending" here, not "safe to treat as
 * consistent" -- reacting to it as if it were consistent would redirect
 * the user to /payment on every single retake regardless of whether that
 * retake actually fixed anything, without ever waiting for the real
 * server verdict. Keying this decision off a ref captured only at arrival
 * makes it immune to that: a live retake changes `completed`/`identityCheck`
 * in the store (so PhotoSetCompleteStep's error display updates correctly),
 * but never re-triggers this effect, since neither is in its dependency
 * list. A full page reload starts a fresh mount, re-fetches, and correctly
 * re-decides from scratch.
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
  const wasConsistentOnFetch = useRef(false)

  useEffect(() => {
    if (!enabled || hasFetched.current) return
    hasFetched.current = true
    photoApi
      .getStatus()
      .then((status) => {
        wasCompletedOnFetch.current = status.completed
        // Completed sets always include identity_check from the API.
        // Treat null as inconsistent only when completed (shouldn't happen
        // on a fresh fetch) so we never bounce past a mismatch.
        wasConsistentOnFetch.current =
          !status.completed || status.identity_check?.consistent === true
        setStatus(status)
      })
      .catch(() => {
        hasFetched.current = false
      })
  }, [enabled, setStatus])

  useEffect(() => {
    if (!completed || !wasCompletedOnFetch.current || !wasConsistentOnFetch.current || pathname !== PHOTOS_PATH) {
      return
    }
    const target = getNextOnboardingStep({
      questionnaireCompleted: true,
      photosCompleted: true,
      photosIdentityConsistent: true, // wasConsistentOnFetch.current already guarantees this
      paymentSucceeded: paymentStatus === "succeeded",
      analysisStatus: analysisStatus ?? "none",
    })
    router.replace(target)
  }, [completed, paymentStatus, analysisStatus, pathname, router])

  return { isChecking: enabled && completed === null }
}
