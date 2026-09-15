"use client"

import { AssessmentOverviewCard } from "./AssessmentOverviewCard"
import { RegionalBalanceBar } from "../../ui/RegionalBalanceBar"
import { SymmetryAxisOverlay } from "../../ui/SymmetryAxisOverlay"
import { meridian } from "@/lib/report/meridianTokens"
import type { FacialAssessment } from "@/lib/reports/reportApi"

export function SymmetryPage({ data, photoUrl }: { data: FacialAssessment; photoUrl: string | null }) {
  return (
    <AssessmentOverviewCard
      id="symmetry"
      title="Symmetry"
      data={data}
      sliderLeftLabel="Asymmetric"
      sliderRightLabel="Symmetric"
    >
      <div className="pt-1">
        <SymmetryAxisOverlay photoUrl={photoUrl} overlay={data.overlay} />
      </div>

      {data.sub_scores && Object.keys(data.sub_scores).length > 0 ? (
        <div className="space-y-3 pt-2">
          <p className="text-[11px] font-semibold tracking-[0.08em] uppercase" style={{ color: meridian.ink.muted }}>
            Regional balance
          </p>
          <div className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
            {Object.entries(data.sub_scores).map(([label, driver]) => (
              <RegionalBalanceBar key={label} label={label} score={driver.score} />
            ))}
          </div>
        </div>
      ) : null}
    </AssessmentOverviewCard>
  )
}
