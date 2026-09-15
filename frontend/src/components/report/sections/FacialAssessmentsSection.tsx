"use client"

import { DimorphismPage } from "./facial-assessments/DimorphismPage"
import { FaceShapePage } from "./facial-assessments/FaceShapePage"
import { PrototypicalityPage } from "./facial-assessments/PrototypicalityPage"
import { ProportionsPage } from "./facial-assessments/ProportionsPage"
import { SymmetryPage } from "./facial-assessments/SymmetryPage"
import { useFrontPhotoUrl } from "@/hooks/useFrontPhotoUrl"
import { meridian } from "@/lib/report/meridianTokens"
import type { ReportFullContent } from "@/lib/reports/reportApi"

export function FacialAssessmentsSection({ full }: { full: ReportFullContent }) {
  const assessments = full.facial_assessments
  // Shared across the 4 pages whose overlays are drawn against the front
  // photo -- fetched once here rather than once per page.
  const photoUrl = useFrontPhotoUrl()

  return (
    <div className="space-y-2.5">
      <h2
        className="px-1 text-xs font-semibold tracking-[0.14em] uppercase"
        style={{ color: meridian.ink.muted }}
      >
        Facial Assessments
      </h2>
      <DimorphismPage data={assessments.dimorphism} />
      <PrototypicalityPage data={assessments.prototypicality} photoUrl={photoUrl} />
      <ProportionsPage data={assessments.proportions} photoUrl={photoUrl} />
      <SymmetryPage data={assessments.symmetry} photoUrl={photoUrl} />
      <FaceShapePage data={assessments.face_shape} photoUrl={photoUrl} />
    </div>
  )
}
