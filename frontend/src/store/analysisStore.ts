import { create } from "zustand"

import type { AnalysisStatus } from "@/lib/analysis/analysisApi"

/**
 * Facial-analysis progress (FR-007, FR-008). Its own store, same
 * module-boundary convention as questionnaireStore/photoStore.
 *
 * Deliberately NOT persisted, same reasoning as photoStore: status is
 * trivially re-fetchable from GET /analysis/status on mount, and there's
 * nothing meaningful to restore verbatim across a reload.
 */
interface AnalysisState {
  /** From GET /analysis/status -- null until fetched once. */
  status: AnalysisStatus | null
  analysisId: string | null

  setStatus: (status: AnalysisStatus, analysisId: string | null) => void
  reset: () => void
}

export const useAnalysisStore = create<AnalysisState>()((set) => ({
  status: null,
  analysisId: null,

  setStatus: (status, analysisId) => set({ status, analysisId }),

  reset: () => set({ status: null, analysisId: null }),
}))
