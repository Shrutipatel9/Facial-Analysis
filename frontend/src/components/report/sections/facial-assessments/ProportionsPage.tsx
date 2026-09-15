"use client"

import { AssessmentOverviewCard } from "./AssessmentOverviewCard"
import { FacialThirdsOverlay } from "../../ui/FacialThirdsOverlay"
import type { FacialAssessment } from "@/lib/reports/reportApi"

export function ProportionsPage({ data, photoUrl }: { data: FacialAssessment; photoUrl: string | null }) {
  return (
    <AssessmentOverviewCard id="proportions" title="Proportions" data={data}>
      <div className="pt-1">
        <FacialThirdsOverlay photoUrl={photoUrl} overlay={data.overlay} />
      </div>
    </AssessmentOverviewCard>
  )
}
