"use client"

import { Progress, ProgressIndicator, ProgressTrack } from "@/components/ui/progress"
import { FEATURE_LABELS, FEATURE_ORDER } from "@/lib/report/reportFeatures"
import { cn } from "@/lib/utils"
import type { FeatureScore } from "@/lib/reports/reportApi"

const NEEDS_ATTENTION_LABEL = "Needs Attention"

/**
 * "Priority Features to Improve" -- the same per-feature scores that back
 * the Overall Score and 2 of the Harmony chart's axes, filtered down to
 * only the features actually flagged "Needs Attention" (the lowest score
 * band), sorted ascending (lowest score = most room to improve, shown
 * first). No new computation -- see
 * facial_assessment_service.compute_feature_scores. Hair/Neck are always
 * omitted here (score=None by design, no CV geometry exists for either),
 * never shown with a fabricated score.
 *
 * report_design_spec.md v3.0 §4.3/§13.1 -- each row also gets a 1-3-line
 * plain-language attribute sub-row (e.g. "Tone Evenness — Noticeably
 * uneven"); this app currently has exactly one driver/finding pair per
 * feature, so exactly one attribute line renders (within the spec's 1-3
 * range, just not the full 3).
 */
export function PriorityFeaturesList({ featureScores }: { featureScores: Record<string, FeatureScore> }) {
  const ranked = FEATURE_ORDER.filter((feature) => {
    const data = featureScores[feature]
    return data?.available === true && data.score !== null && data.label === NEEDS_ATTENTION_LABEL
  })
    .map((feature) => ({
      feature,
      score: featureScores[feature].score as number,
      driver: featureScores[feature].driver,
      finding: featureScores[feature].finding,
    }))
    .sort((a, b) => a.score - b.score)

  if (ranked.length === 0) {
    return <p className="text-sm text-muted-foreground">No features are flagged as needing attention in this report.</p>
  }

  return (
    <ul className="space-y-3">
      {ranked.map(({ feature, score, driver, finding }) => {
        const rounded = Math.round(score)
        const tone = scoreTone(rounded)
        return (
          <li key={feature} className="space-y-1.5">
            <div className="flex items-baseline justify-between gap-3 text-sm">
              <p className="min-w-0 truncate font-medium text-foreground">{FEATURE_LABELS[feature]}</p>
              <span className={cn("shrink-0 text-sm font-semibold tabular-nums", tone.scoreClass)}>
                {rounded}
              </span>
            </div>
            {driver && finding ? (
              <p className={cn("text-xs", tone.labelClass)}>
                {driver} — {finding}
              </p>
            ) : null}
            <Progress value={score} className="gap-0">
              <ProgressTrack className="h-1.5 bg-muted/80">
                <ProgressIndicator className={tone.barClass} />
              </ProgressTrack>
            </Progress>
          </li>
        )
      })}
    </ul>
  )
}

function scoreTone(score: number) {
  if (score < 50) {
    return {
      labelClass: "text-amber-700/80",
      scoreClass: "text-amber-800",
      barClass: "bg-amber-600",
    }
  }
  if (score < 80) {
    return {
      labelClass: "text-muted-foreground",
      scoreClass: "text-foreground",
      barClass: "bg-primary/80",
    }
  }
  return {
    labelClass: "text-muted-foreground",
    scoreClass: "text-primary",
    barClass: "bg-primary",
  }
}
