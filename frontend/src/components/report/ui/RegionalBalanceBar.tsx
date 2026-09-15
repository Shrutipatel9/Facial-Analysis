"use client"

import { Progress, ProgressIndicator, ProgressTrack } from "@/components/ui/progress"
import { meridian, scoreStateTone } from "@/lib/report/meridianTokens"

/**
 * Compact labeled bar for a grid of related sub-scores -- Symmetry's
 * 4-item "Regional Balance" grid and Dimorphism's per-feature grid share
 * this, both being "one row per named sub-score" layouts. Score-only by
 * design -- no finding statement alongside the bar.
 */
export function RegionalBalanceBar({ label, score }: { label: string; score: number }) {
  return (
    <div className="space-y-1">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-xs font-medium" style={{ color: meridian.ink.primary }}>
          {label}
        </span>
        <span className="text-xs font-semibold tabular-nums" style={{ color: meridian.ink.primary }}>
          {Math.round(score)}
        </span>
      </div>
      <Progress value={score} className="gap-0">
        <ProgressTrack className="h-1" style={{ backgroundColor: meridian.surface.recessed }}>
          <ProgressIndicator style={{ backgroundColor: scoreStateTone(score) }} />
        </ProgressTrack>
      </Progress>
    </div>
  )
}
