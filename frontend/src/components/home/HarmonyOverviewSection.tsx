import { Activity } from "lucide-react"

import { HarmonyRadarChart } from "@/components/dashboard/HarmonyRadarChart"
import { FEATURE_LABELS, FEATURE_ORDER } from "@/lib/report/reportFeatures"
import type { ReportOut } from "@/lib/reports/reportApi"

/**
 * Home Overview "Harmony Profile & Overview" block. Feature Evaluation is
 * a 3-column grid (Zone / Finding / Reference), per report_design_spec.md
 * v3.0 §13.2 / report_template.md v3.0 §3.8 — Zone uses the app's existing
 * 11 report features (not the reference's own unresolved 5-zone
 * taxonomy). Finding is the short plain-language phrase already computed
 * for the Priority Features list (FeatureScore.finding); Reference is a
 * formatted typical/benchmark value (FeatureScore.reference_value), an
 * empty cell — never a fabricated one — where none exists.
 */
export function HarmonyOverviewSection({ report }: { report: ReportOut }) {
  const { full, teaser } = report

  return (
    <div className="flex h-fit w-full flex-col gap-5 rounded-2xl border border-border/80 bg-card p-5 shadow-[0_10px_30px_-18px_rgba(20,55,75,0.28)]">
      <div className="flex items-center gap-2.5">
        <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground">
          <Activity className="size-3.5" />
        </span>
        <h2 className="font-heading text-base font-semibold tracking-tight">Harmony Profile & Overview</h2>
      </div>

      <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-2">
        <div>
          <h3 className="mb-2 text-xs font-semibold tracking-[0.1em] text-muted-foreground uppercase">Harmony</h3>
          <HarmonyRadarChart harmonyChart={full.harmony_chart} heightClassName="h-72" />
        </div>
        {teaser.intro ? (
          <div>
            <h3 className="mb-2 text-xs font-semibold tracking-[0.1em] text-muted-foreground uppercase">Overview</h3>
            <p className="text-sm leading-relaxed text-muted-foreground">{teaser.intro}</p>
          </div>
        ) : null}
      </div>

      <div>
        <h3 className="mb-3 text-xs font-semibold tracking-[0.1em] text-muted-foreground uppercase">
          Feature Evaluation
        </h3>

        <div className="overflow-hidden rounded-xl border border-border/70">
          <div className="hidden grid-cols-[6.5rem_1fr_8rem] gap-4 border-b border-border/70 bg-muted/40 px-4 py-2.5 text-[11px] font-semibold tracking-[0.08em] text-muted-foreground uppercase sm:grid">
            <span>Zone</span>
            <span>Finding</span>
            <span className="text-right">Reference</span>
          </div>

          <ul>
            {FEATURE_ORDER.map((feature) => {
              const scoreData = full.feature_scores[feature]
              const finding = scoreData?.finding ?? scoreData?.note ?? "—"
              const reference = scoreData?.reference_value ?? "—"

              return (
                <li
                  key={feature}
                  className="grid grid-cols-1 gap-1.5 border-b border-border/50 px-4 py-3 last:border-b-0 sm:grid-cols-[6.5rem_1fr_8rem] sm:items-center sm:gap-4"
                >
                  <p className="text-sm font-semibold text-foreground">{FEATURE_LABELS[feature]}</p>
                  <p className="text-sm text-muted-foreground">{finding}</p>
                  <p className="text-right text-sm text-muted-foreground sm:text-right">{reference}</p>
                </li>
              )
            })}
          </ul>
        </div>
      </div>
    </div>
  )
}
