"use client"

import { AssessmentOverviewCard } from "./AssessmentOverviewCard"
import { FaceShapeWireframe } from "../../ui/FaceShapeWireframe"
import type { FacialAssessment } from "@/lib/reports/reportApi"

export function PrototypicalityPage({ data, photoUrl }: { data: FacialAssessment; photoUrl: string | null }) {
  return (
    <AssessmentOverviewCard
      id="prototypicality"
      title="Prototypicality"
      data={data}
      sliderLeftLabel="Distinctive"
      sliderRightLabel="Highly Typical"
    >
      <div className="pt-1">
        <FaceShapeWireframe photoUrl={photoUrl} overlay={data.overlay} />
      </div>
    </AssessmentOverviewCard>
  )
}
