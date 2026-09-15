import { CalendarClock } from "lucide-react"

import type { FacialAge } from "@/lib/reports/reportApi"

const MIN_AGE = 5
const MAX_AGE = 65

/**
 * Home Overview "Facial Age" card (report_design_spec.md v3.0 §4.4/§15) --
 * a single current-estimate read, never a projection: one numeral plus a
 * read-only range track with a single pointer at the estimate. Not an
 * input control (report_design_spec.md §15 explicitly treats this as a
 * read-only visualization, so this renders a plain positioned marker, not
 * a real `<input type="range">`). Omitted by the caller entirely
 * (HomeOverviewScreen.tsx) whenever `facialAge` is null -- never a
 * fabricated/default estimate.
 */
export function FacialAgeCard({ facialAge }: { facialAge: FacialAge }) {
  const clamped = Math.min(MAX_AGE, Math.max(MIN_AGE, facialAge.estimate))
  const percent = ((clamped - MIN_AGE) / (MAX_AGE - MIN_AGE)) * 100

  return (
    <div className="h-fit w-full rounded-2xl border border-border/80 bg-card p-5 shadow-[0_10px_30px_-18px_rgba(20,55,75,0.28)]">
      <div className="mb-4 flex items-center gap-2.5">
        <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground">
          <CalendarClock className="size-3.5" />
        </span>
        <h2 className="font-heading text-base font-semibold tracking-tight">Facial Age</h2>
      </div>

      <p className="font-heading text-3xl font-semibold tabular-nums text-foreground">{facialAge.estimate}</p>
      {facialAge.note ? <p className="mt-1 text-sm text-muted-foreground">{facialAge.note}</p> : null}

      <div className="mt-4" role="img" aria-label={`Estimated facial age ${facialAge.estimate}, on a ${MIN_AGE} to ${MAX_AGE} scale`}>
        <div className="relative h-1.5 rounded-full bg-muted/80">
          <div
            className="absolute top-1/2 size-3.5 -translate-y-1/2 -translate-x-1/2 rounded-full border-2 border-card bg-primary shadow"
            style={{ left: `${percent}%` }}
          />
        </div>
        <div className="mt-1.5 flex justify-between text-[11px] text-muted-foreground">
          <span>{MIN_AGE}</span>
          <span>{MAX_AGE}</span>
        </div>
      </div>
    </div>
  )
}
