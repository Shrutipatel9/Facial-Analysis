import { formatDuration } from "@/lib/format"
import type { ReportOut } from "@/lib/reports/reportApi"
import { evaluatedPointsCount } from "@/lib/reports/reportStats"
import { cn } from "@/lib/utils"

/**
 * Home Overview stat row (spec §1.2) -- three equal summary cards.
 */
export function StatRow({ report }: { report: ReportOut }) {
  const { count, total } = evaluatedPointsCount(report.full)
  const durationSeconds = report.full.analysis_duration_seconds

  const stats: { label: string; value: string; accent?: boolean }[] = []
  if (report.full.overall_score !== null) {
    stats.push({ label: "Overall Score", value: `${Math.round(report.full.overall_score)} / 100` })
  }
  if (total > 0) {
    stats.push({ label: "Evaluated", value: `${count} / ${total} points`, accent: true })
  }
  if (durationSeconds !== null) {
    stats.push({ label: "Analysis Time", value: formatDuration(durationSeconds) })
  }

  if (stats.length === 0) return null

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      {stats.map((stat) => (
        <div
          key={stat.label}
          className="rounded-2xl border border-border/80 bg-card px-5 py-4 shadow-[0_10px_30px_-18px_rgba(20,55,75,0.28)]"
        >
          <p className="text-[11px] font-semibold tracking-[0.1em] text-muted-foreground uppercase">
            {stat.label}
          </p>
          <p
            className={cn(
              "mt-1.5 font-heading text-2xl font-semibold tracking-tight",
              stat.accent ? "text-primary" : "text-foreground"
            )}
          >
            {stat.value}
          </p>
        </div>
      ))}
    </div>
  )
}
