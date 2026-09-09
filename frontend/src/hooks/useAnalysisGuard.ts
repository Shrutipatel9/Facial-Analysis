"use client"

import { useEffect, useRef } from "react"

import * as analysisApi from "@/lib/analysis/analysisApi"
import { useAnalysisStore } from "@/store/analysisStore"

/**
 * Loads analysis status once. Deliberately does NOT redirect anywhere once
 * analysis completes -- AnalysisScreen.tsx's own "completed" state owns
 * that moment (an "Analysis complete" screen with a manual "View report"
 * button to /report), the same way PhotoSetCompleteStep owns the photo
 * completion moment (see usePhotoUploadGuard's docstring). An earlier
 * version of this hook auto-redirected /analysis -> /dashboard the instant
 * status flipped to "completed" -- the user explicitly asked for that
 * removed: completing analysis must never auto-navigate to /dashboard, the
 * user decides when to view their report, and /dashboard only becomes
 * reachable (via the nav link in (protected)/layout.tsx) once a report
 * actually exists.
 *
 * Does NOT redirect an incomplete user away from /dashboard itself --
 * that decision is centralized in useOnboardingEntryGuard
 * ((protected)/layout.tsx). See useQuestionnaireGuard's docstring for why
 * (a redirect race that could send a brand-new user anywhere in the chain).
 *
 * Only enabled once the photo guard has already cleared (a user can't
 * sensibly reach /analysis before finishing photos) -- see
 * (protected)/layout.tsx's wiring.
 */
export function useAnalysisGuard(enabled: boolean): { isChecking: boolean } {
  const status = useAnalysisStore((state) => state.status)
  const setStatus = useAnalysisStore((state) => state.setStatus)
  const hasFetched = useRef(false)

  useEffect(() => {
    if (!enabled || hasFetched.current) return
    hasFetched.current = true
    analysisApi
      .getStatus()
      .then((result) => setStatus(result.status, result.analysis_id))
      .catch(() => {
        hasFetched.current = false
      })
  }, [enabled, setStatus])

  return { isChecking: enabled && status === null }
}
