"use client"

import { AssessmentOverviewCard } from "./AssessmentOverviewCard"
import { FaceShapeWireframe } from "../../ui/FaceShapeWireframe"
import { ScoreSlider } from "../../ui/ScoreSlider"
import type { FacialAssessment } from "@/lib/reports/reportApi"

export function FaceShapePage({ data, photoUrl }: { data: FacialAssessment; photoUrl: string | null }) {
  return (
    <AssessmentOverviewCard id="face_shape" title="Face Shape" data={data}>
      <div className="pt-1">
        <FaceShapeWireframe photoUrl={photoUrl} overlay={data.overlay} />
      </div>
      {data.score !== null && data.score !== undefined ? (
        <div className="pt-2">
          {/* "Angular <-> Soft" is an invented placeholder axis, not a
              confirmed reference label -- see data.note above. */}
          <ScoreSlider value={data.score} leftLabel="Angular" rightLabel="Soft" />
        </div>
      ) : null}
    </AssessmentOverviewCard>
  )
}
