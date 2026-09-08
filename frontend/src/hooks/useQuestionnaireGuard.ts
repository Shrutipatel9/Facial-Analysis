"use client"

import { usePathname, useRouter } from "next/navigation"
import { useEffect, useRef } from "react"

import * as questionnaireApi from "@/lib/questionnaire/questionnaireApi"
import { useQuestionnaireStore } from "@/store/questionnaireStore"

const QUESTIONNAIRE_PATH = "/questionnaire"
const DASHBOARD_PATH = "/dashboard"

/**
 * Loads onboarding status and routes:
 * - incomplete → /questionnaire (skip dashboard landing)
 * - complete on /questionnaire → /dashboard
 */
export function useQuestionnaireGuard(enabled: boolean): { isChecking: boolean } {
  const completed = useQuestionnaireStore((state) => state.completed)
  const setCompleted = useQuestionnaireStore((state) => state.setCompleted)
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
    if (completed === null) return
    if (!completed && pathname === DASHBOARD_PATH) {
      router.replace(QUESTIONNAIRE_PATH)
      return
    }
    if (completed && pathname === QUESTIONNAIRE_PATH) {
      router.replace(DASHBOARD_PATH)
    }
  }, [completed, pathname, router])

  return { isChecking: enabled && completed === null }
}
