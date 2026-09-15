"use client"

import { Progress, ProgressIndicator, ProgressTrack } from "@/components/ui/progress"
import { meridian, scoreStateTone } from "@/lib/report/meridianTokens"

/**
 * Read-only labeled 0-100 bar shared by every Facial Assessments page --
 * built on the existing Progress primitive (base-ui Track/Indicator)
 * rather than a new hand-rolled bar, per report_design_spec.md's "one
 * component vocabulary reused everywhere" rule.
 */
export function ScoreSlider({
  value,
  leftLabel,
  rightLabel,
}: {
  value: number
  leftLabel?: string
  rightLabel?: string
}) {
  return (
    <div className="space-y-1.5">
      <Progress value={value} className="gap-0">
        <ProgressTrack style={{ backgroundColor: meridian.surface.recessed }}>
          <ProgressIndicator style={{ backgroundColor: scoreStateTone(value) }} />
        </ProgressTrack>
      </Progress>
      {leftLabel || rightLabel ? (
        <div className="flex justify-between text-[11px]" style={{ color: meridian.ink.muted }}>
          <span>{leftLabel}</span>
          <span>{rightLabel}</span>
        </div>
      ) : null}
    </div>
  )
}
