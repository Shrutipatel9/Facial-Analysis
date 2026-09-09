import { create } from "zustand"

import type { ReportOut } from "@/lib/reports/reportApi"

/**
 * The generated report (FR-009-FR-014). Its own store, same
 * module-boundary convention as questionnaireStore/photoStore/analysisStore.
 *
 * Deliberately NOT persisted, same reasoning as analysisStore: cheaply
 * re-fetchable via GET /reports on mount, nothing meaningful to restore
 * verbatim across a reload.
 */
interface ReportState {
  report: ReportOut | null
  /** null until GET /reports (or setReport) has answered once this session. */
  hasReport: boolean | null

  setReport: (report: ReportOut) => void
  setHasReport: (value: boolean) => void
  reset: () => void
}

export const useReportStore = create<ReportState>()((set) => ({
  report: null,
  hasReport: null,

  setReport: (report) => set({ report, hasReport: true }),

  setHasReport: (value) => set({ hasReport: value }),

  reset: () => set({ report: null, hasReport: null }),
}))
