"use client"

import { usePathname, useRouter } from "next/navigation"
import { useEffect, useRef } from "react"

import { getNextOnboardingStep } from "@/lib/onboarding/nextStep"
import * as paymentApi from "@/lib/payments/paymentApi"
import { useAnalysisStore } from "@/store/analysisStore"
import { usePaymentStore } from "@/store/paymentStore"

const PAYMENT_PATH = "/payment"

/**
 * Loads payment status and bounces a user who has ALREADY paid away from
 * its own page -- to whichever step is actually next
 * (getNextOnboardingStep), same shape as usePhotoUploadGuard/
 * useQuestionnaireGuard.
 *
 * Does NOT redirect an incomplete user away from /dashboard itself --
 * that decision is centralized in useOnboardingEntryGuard
 * ((protected)/layout.tsx). See useQuestionnaireGuard's docstring for why
 * (a redirect race that could send a brand-new user anywhere in the chain).
 *
 * Only enabled once the photo guard has already cleared (a user can't
 * sensibly reach /payment before finishing photos) -- see
 * (protected)/layout.tsx's wiring.
 */
export function usePaymentGuard(enabled: boolean): { isChecking: boolean } {
  const status = usePaymentStore((state) => state.status)
  const setStatus = usePaymentStore((state) => state.setStatus)
  const analysisStatus = useAnalysisStore((state) => state.status)
  const pathname = usePathname()
  const router = useRouter()
  const hasFetched = useRef(false)

  useEffect(() => {
    if (!enabled || hasFetched.current) return
    hasFetched.current = true
    paymentApi
      .getStatus()
      .then((result) => setStatus(result.status, result.price_cents, result.price_currency))
      .catch(() => {
        hasFetched.current = false
      })
  }, [enabled, setStatus])

  useEffect(() => {
    if (status !== "succeeded" || pathname !== PAYMENT_PATH) return
    const target = getNextOnboardingStep({
      questionnaireCompleted: true,
      photosCompleted: true,
      paymentSucceeded: true,
      analysisStatus: analysisStatus ?? "none",
    })
    router.replace(target)
  }, [status, analysisStatus, pathname, router])

  return { isChecking: enabled && status === null }
}
