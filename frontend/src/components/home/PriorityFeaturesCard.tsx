import { ListChecks } from "lucide-react"

import { PriorityFeaturesList } from "@/components/dashboard/PriorityFeaturesList"
import type { FeatureScore } from "@/lib/reports/reportApi"

/**
 * Home Overview "Priority Features to Improve" card (spec §1.5) -- reuses
 * the existing PriorityFeaturesList (real feature_scores, lowest-first,
 * Hair/Neck omitted since they have no CV score by design).
 */
export function PriorityFeaturesCard({ featureScores }: { featureScores: Record<string, FeatureScore> }) {
  return (
    <div className="h-fit w-full rounded-2xl border border-border/80 bg-card p-5 shadow-[0_10px_30px_-18px_rgba(20,55,75,0.28)]">
      <div className="mb-4 flex items-center gap-2.5">
        <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground">
          <ListChecks className="size-3.5" />
        </span>
        <h2 className="font-heading text-base font-semibold tracking-tight">Priority Features to Improve</h2>
      </div>
      <PriorityFeaturesList featureScores={featureScores} />
    </div>
  )
}
