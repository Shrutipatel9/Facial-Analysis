import { create } from "zustand"
import { persist } from "zustand/middleware"

import type { AnswerValue } from "@/lib/questionnaire/questionnaireApi"

/**
 * Onboarding-questionnaire progress. Deliberately its OWN store, not part
 * of authStore -- per docs/architecture.md §5's module-boundary convention
 * and docs/phase-wise-requirements.md's own note that this is "regular app
 * state, not auth state."
 *
 * Unlike authStore (which must NEVER use `persist` -- see its docstring),
 * this store IS wrapped in `persist` (localStorage) on purpose: that rule
 * is specific to bearer-token material being JS-readable, not a blanket
 * ban. In-progress answers here are ordinary form content (occupation,
 * smoking/drinking frequency, self-perceived features) with no comparable
 * security exposure, and losing 20 answered questions to an accidental
 * reload is a real UX cost with no security upside to avoiding it.
 */
interface QuestionnaireState {
  answers: Record<string, AnswerValue>
  currentQuestionId: string | null
  disclaimerAccepted: boolean
  /** From GET /questionnaire/status -- null until fetched once. */
  completed: boolean | null

  setAnswer: (id: string, value: AnswerValue) => void
  goTo: (id: string) => void
  setDisclaimerAccepted: (value: boolean) => void
  setCompleted: (value: boolean) => void
  /** Clears in-progress wizard fields only — keeps `completed` (post-submit). */
  reset: () => void
  /** Full wipe for logout / account switch — including `completed` and localStorage. */
  clearForNewSession: () => void
}

const initialState = {
  answers: {},
  currentQuestionId: null,
  disclaimerAccepted: false,
  completed: null,
} satisfies Partial<QuestionnaireState>

export const useQuestionnaireStore = create<QuestionnaireState>()(
  persist(
    (set) => ({
      ...initialState,

      setAnswer: (id, value) =>
        set((state) => ({ answers: { ...state.answers, [id]: value } })),

      goTo: (id) => set({ currentQuestionId: id }),

      setDisclaimerAccepted: (value) => set({ disclaimerAccepted: value }),

      setCompleted: (value) => set({ completed: value }),

      // Deliberately does NOT reset `completed` -- that field is owned by
      // useQuestionnaireGuard's status check, not wizard progress, and the
      // guard hook instance persists across the same-layout client-side
      // navigation from /questionnaire to /dashboard after a successful
      // submit (see QuestionnaireWizard's onSubmit, which calls
      // setCompleted(true) itself). Resetting it here would race that call
      // and could leave the guard stuck showing its loading state.
      reset: () => set({ answers: {}, currentQuestionId: null, disclaimerAccepted: false }),

      clearForNewSession: () => {
        set({ ...initialState })
        // Drop persisted answers so the next account doesn't inherit them.
        useQuestionnaireStore.persist.clearStorage()
      },
    }),
    {
      name: "questionnaire-progress",
      // completed/currentQuestionId are session-derived/navigation state,
      // not meaningful to restore verbatim across a reload the way answers
      // are -- only persist the actual in-progress content.
      partialize: (state) => ({ answers: state.answers, disclaimerAccepted: state.disclaimerAccepted }),
    }
  )
)
