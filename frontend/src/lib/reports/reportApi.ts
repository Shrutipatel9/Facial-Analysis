import { authenticatedBlobRequest, authenticatedRequest } from "@/lib/api/apiClient"

export interface ReportMeasurement {
  available: boolean
  metrics: Record<string, number> | null
  note: string | null
}

// FR-025 (Milestone 3) -- one protocol/recommendation line item's
// structured metadata. Every field but `text` is nullable: the AI/report-
// assembly layer never fabricates a value it isn't confident about
// (Backend/app/services/report_assembly_service.py's
// _normalize_recommendation_item) -- render an omitted badge, never a
// placeholder, when a field is null.
export interface RecommendationItem {
  text: string
  // Approximate USD estimate/range (e.g. "$15-25"), informational only --
  // never a guaranteed price (FR-012).
  cost: string | null
  cadence: string | null
  time_to_effect: string | null
  // Exactly "Easy" | "Medium" | "Hard" -- any other value is dropped
  // server-side, never passed through as free text.
  difficulty: "Easy" | "Medium" | "Hard" | null
  // FR-024 (Milestone 3) -- paired with the feature's existing before/
  // after image (BeforeAfterBlock) for the first recommendation per
  // feature only; every item still carries these tags regardless.
  category: "Cosmetic" | "Lifestyle" | "Clinical" | null
  risk_level: "Low" | "Medium" | "High" | null
  product_or_method: string | null
}

export interface ReportFeatureSection {
  // Named narrative sub-sections (e.g. hair's "Hair Style"/"Hair Loss"/
  // "Hair Health") -- see Backend/app/services/ai_narrative_service.py's
  // _FEATURE_SUBSECTIONS. Replaces a single `narrative: string` field
  // (matching the client reference report's own multi-sub-section depth
  // per feature). Empty for a pre-this-change report or when nothing was
  // confidently written -- never fabricated. Iterate with
  // Object.entries(...) -- already in the correct display order.
  sections: Record<string, string>
  summary_callout: string
  strengths: string
  areas_of_note: string
  projected_potential: RecommendationItem[]
  // AI-classified named attributes for this feature (e.g. hair's
  // hairline/texture/density), matching the depth of the client's own
  // reference report. Empty for a pre-this-change report or when nothing
  // was confidently assessable -- never fabricated.
  attributes: Record<string, string>
  measurement: ReportMeasurement
  has_image: boolean
  // Milestone 2 (FR-022): "not_attempted" | "pending" | "generating" |
  // "generated" | "failed" -- see BeforeAfterBlock.
  visual_status: string
}

export interface ReportTeaser {
  intro: string
  feature_summaries: Record<string, string>
}

// Milestone 2 (FR-018) -- one named contributor to an assessment, e.g. one
// of Dimorphism's top-3 drivers or one of Symmetry's Regional Balance rows.
export interface AssessmentDriver {
  feature: string
  score: number
  label: string
  citation: string
}

// Milestone 2 (FR-018) -- one of the 5 Facial Assessments. Every field is
// nullable/absent when `available` is false (no face detected, etc.) --
// never render a fabricated score.
export interface FacialAssessment {
  available: boolean
  score: number | null
  label: string | null
  slider_position: number | null
  drivers: AssessmentDriver[] | null
  sub_scores: Record<string, AssessmentDriver> | null
  overlay: Record<string, unknown> | null
  note: string | null
}

// Milestone 2 -- one 0-100 score + label per report feature, backs Overall
// Score / Priority Features to Improve / 2 of the Harmony chart's axes.
export interface FeatureScore {
  available: boolean
  score: number | null
  label: string | null
  note: string | null
  // Short (1-2 word) dimension the score measures, e.g. "Width",
  // "Projection" -- backs the Priority Features list's "what to improve".
  driver: string | null
  // report_design_spec.md v3.0 §13.1/§13.2 -- a short plain-language
  // phrase for `driver` (e.g. "Wider than typical"), shared by the
  // Priority Features sub-rows and the Feature Evaluation table's
  // "Finding" column. Null where no directional/magnitude read applies.
  finding: string | null
  // report_template.md v3.0 §3.8 -- a formatted typical/benchmark value
  // for `driver`, e.g. "~60% of face width". Null where no single
  // reference value exists -- renders as an empty cell, never fabricated.
  reference_value: string | null
}

// report_design_spec.md v3.0 §15 -- a single current-estimate read (never
// a projection). Absent entirely (not the whole ReportFullContent's
// `facial_age` key defaulted to some zero-ish shape) whenever the AI
// narrative call couldn't confidently estimate it.
export interface FacialAge {
  estimate: number
  note: string | null
}

// report_design_spec.md v3.0 §13.3 -- maps to the Hair page's illustrated
// 7-stage strip (Normal -> Need Attention -> Extreme).
export interface HairLoss {
  stage: number
  label: string
}

export const ASSESSMENT_ORDER = ["dimorphism", "prototypicality", "proportions", "symmetry", "face_shape"] as const

export const ASSESSMENT_LABELS: Record<string, string> = {
  dimorphism: "Dimorphism",
  prototypicality: "Prototypicality",
  proportions: "Proportions",
  symmetry: "Symmetry",
  face_shape: "Face Shape",
}

export const HARMONY_AXES = ["harmony", "symmetry", "smoothness", "jawline", "skin", "volume"] as const

export interface ReportFullContent {
  understanding_your_results: string
  limitations: string
  features: Record<string, ReportFeatureSection>
  recommendations: {
    at_home: RecommendationItem[]
    otc_skincare: RecommendationItem[]
    in_clinic: RecommendationItem[]
  }
  closing_recommendations: string
  // Milestone 2 -- always all 5 ASSESSMENT_ORDER keys, all-unavailable for
  // a pre-Milestone-2 report.
  facial_assessments: Record<string, FacialAssessment>
  // Milestone 2 -- always all 11 report-feature keys.
  feature_scores: Record<string, FeatureScore>
  overall_score: number | null
  // Milestone 2 -- always all 6 HARMONY_AXES keys.
  harmony_chart: Record<string, number | null>
  // report_design_spec.md v3.0 §15/§13.3 -- both null whenever the AI
  // narrative call couldn't confidently estimate them, or for any report
  // generated before this field existed. Never fabricated/defaulted.
  facial_age: FacialAge | null
  hair_loss: HairLoss | null
  // Dashboard consolidation -- real elapsed CV+AI pipeline time; null
  // whenever narrative generation is still pending/failed. Never a
  // fabricated value -- see Backend/app/api/routers/reports.py's
  // _to_report_out.
  analysis_duration_seconds: number | null
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

/** Milestone 2 (FR-022) AI-generated before/after image -- only call when
 * that feature's `visual_status` is "generated", otherwise this 404s. */
export function getFeatureVisual(reportId: string, feature: string): Promise<Blob> {
  return authenticatedBlobRequest(`/reports/${reportId}/features/${feature}/visual`)
}

/** Lightweight polling endpoint -- {feature: status} for all 11 features. */
export function getVisualsStatus(reportId: string): Promise<Record<string, string>> {
  return authenticatedRequest<Record<string, string>>(`/reports/${reportId}/visuals/status`, { method: "GET" })
}
