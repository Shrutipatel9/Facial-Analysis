import { authenticatedRequest } from "@/lib/api/apiClient"

export type AnalysisStatus = "none" | "processing" | "completed" | "failed"

export interface AnalysisStatusResponse {
  status: AnalysisStatus
  analysis_id: string | null
}

export interface AnalysisFeatureResult {
  narrative: string
  summary_callout: string
  recommendation_ideas: string[]
}

export interface NarrativeResult {
  features: Record<string, AnalysisFeatureResult>
  closing_recommendations: string
}

export interface AnalysisMeasurement {
  available: boolean
  metrics: Record<string, number> | null
  note: string | null
}

export interface AnalysisOut {
  id: string
  status: "processing" | "completed" | "failed"
  measurements: Record<string, AnalysisMeasurement>
  narrative_result: NarrativeResult | null
  error_message: string | null
  created_at: string
  completed_at: string | null
}

export interface TriggerAnalysisResponse {
  id: string
  status: "processing"
}

export function triggerAnalysis(): Promise<TriggerAnalysisResponse> {
  return authenticatedRequest<TriggerAnalysisResponse>("/analysis", { method: "POST" })
}

export function getStatus(): Promise<AnalysisStatusResponse> {
  return authenticatedRequest<AnalysisStatusResponse>("/analysis/status", { method: "GET" })
}

export function getAnalysis(id: string): Promise<AnalysisOut> {
  return authenticatedRequest<AnalysisOut>(`/analysis/${id}`, { method: "GET" })
}
