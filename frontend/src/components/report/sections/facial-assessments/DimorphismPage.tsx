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
        <div className="space-y-1.5 pt-1">
          <p className="text-[11px] font-semibold tracking-[0.08em] uppercase" style={{ color: meridian.ink.muted }}>
            Top drivers
          </p>
          <ul className="space-y-1.5 text-sm" style={{ color: meridian.ink.muted }}>
            {data.drivers.map((driver) => (
              <li key={driver.feature} className="flex justify-between gap-3">
                <span>{FEATURE_LABELS[driver.feature] ?? driver.feature}</span>
                <span className="shrink-0 font-medium tabular-nums" style={{ color: meridian.ink.primary }}>
                  {Math.round(driver.score)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {data.sub_scores && Object.keys(data.sub_scores).length > 0 ? (
        <div className="space-y-3 pt-2">
          <p className="text-[11px] font-semibold tracking-[0.08em] uppercase" style={{ color: meridian.ink.muted }}>
            Per-feature breakdown
          </p>
          <div className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
            {Object.entries(data.sub_scores).map(([feature, driver]) => (
              <RegionalBalanceBar key={feature} label={FEATURE_LABELS[feature] ?? feature} score={driver.score} />
            ))}
          </div>
        </div>
      ) : null}
    </AssessmentOverviewCard>
  )
}
