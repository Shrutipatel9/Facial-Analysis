"use client"

import { AssessmentOverviewCard } from "./AssessmentOverviewCard"
import { RegionalBalanceBar } from "../../ui/RegionalBalanceBar"
import { meridian } from "@/lib/report/meridianTokens"
import { FEATURE_LABELS } from "@/lib/report/reportFeatures"
import type { FacialAssessment } from "@/lib/reports/reportApi"

export function DimorphismPage({ data }: { data: FacialAssessment }) {
  return (
    <AssessmentOverviewCard
      id="dimorphism"
      title="Dimorphism"
      data={data}
      sliderLeftLabel="Hyper Feminine"
      sliderRightLabel="Hyper Masculine"
    >
      {data.drivers && data.drivers.length > 0 ? (
        <div className="max-w-md space-y-2 pt-1">
          <p className="text-[11px] font-semibold tracking-[0.08em] uppercase" style={{ color: meridian.ink.muted }}>
            Top drivers
          </p>
          <div className="space-y-2.5">
            {data.drivers.map((driver) => (
              <RegionalBalanceBar
                key={driver.feature}
                label={FEATURE_LABELS[driver.feature] ?? driver.feature}
                score={driver.score}
              />
            ))}
          </div>
        </div>
      ) : null}

      {data.sub_scores && Object.keys(data.sub_scores).length > 0 ? (
        <div className="space-y-3 pt-2">
          <p className="text-[11px] font-semibold tracking-[0.08em] uppercase" style={{ color: meridian.ink.muted }}>
            Per-feature breakdown
          </p>
          <div className="grid max-w-2xl gap-x-5 gap-y-3 sm:grid-cols-2">
            {Object.entries(data.sub_scores).map(([feature, driver]) => (
              <RegionalBalanceBar key={feature} label={FEATURE_LABELS[feature] ?? feature} score={driver.score} />
            ))}
          </div>
        </div>
      ) : null}
    </AssessmentOverviewCard>
  )
}
