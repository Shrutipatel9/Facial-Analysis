import { authenticatedBlobRequest, authenticatedRequest } from "@/lib/api/apiClient"

export interface ReportMeasurement {
  available: boolean
  metrics: Record<string, number> | null
  note: string | null
}

export interface ReportFeatureSection {
  narrative: string
  summary_callout: string
  strengths: string
  areas_of_note: string
  projected_potential: string[]
  measurement: ReportMeasurement
  has_image: boolean
}

export interface ReportTeaser {
  intro: string
  feature_summaries: Record<string, string>
}

export interface ReportFullContent {
  understanding_your_results: string
  limitations: string
  features: Record<string, ReportFeatureSection>
  recommendations: {
    at_home: string[]
    otc_skincare: string[]
    in_clinic: string[]
  }
  closing_recommendations: string
}

export interface ReportOut {
  id: string
  publish_state: string
  created_at: string
  teaser: ReportTeaser
  // Always populated -- a Report can only ever be created from an
  // already-paid, already-completed analysis (payment gates the START of
  // analysis itself, see Backend/app/services/analysis_service.py's
  // trigger_analysis), so there is no unpaid/partial state to represent.
  full: ReportFullContent
}

export interface ReportSummary {
  id: string
  publish_state: string
  created_at: string
}

/** Idempotent -- safe to call even if a report already exists for this user. */
export function generateReport(): Promise<ReportOut> {
  return authenticatedRequest<ReportOut>("/reports", { method: "POST" })
}

export function listReports(): Promise<ReportSummary[]> {
  return authenticatedRequest<ReportSummary[]>("/reports", { method: "GET" })
}

export function getReport(id: string): Promise<ReportOut> {
  return authenticatedRequest<ReportOut>(`/reports/${id}`, { method: "GET" })
}

export function downloadPdf(id: string): Promise<Blob> {
  return authenticatedBlobRequest(`/reports/${id}/pdf`)
}

/** Cropped region of the front photo for one feature -- only call when
 * that feature's `has_image` is true, otherwise this 404s. */
export function getFeatureImage(reportId: string, feature: string): Promise<Blob> {
  return authenticatedBlobRequest(`/reports/${reportId}/features/${feature}/image`)
}
