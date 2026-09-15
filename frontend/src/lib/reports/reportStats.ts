import type { ReportFullContent } from "./reportApi"

/**
 * Dashboard "Evaluated points" stat -- a real count of how much of the
 * report is actually populated (feature_scores + facial_assessments, both
 * already-computed data), not a fabricated marketing number. Pure frontend
 * derivation, no backend change needed since both inputs are already on
 * ReportFullContent.
 */
export function evaluatedPointsCount(full: ReportFullContent): { count: number; total: number } {
  const featureCount = Object.values(full.feature_scores).filter((entry) => entry.available).length
  const assessmentCount = Object.values(full.facial_assessments).filter((entry) => entry.available).length
  return {
    count: featureCount + assessmentCount,
    total: Object.keys(full.feature_scores).length + Object.keys(full.facial_assessments).length,
  }
}
