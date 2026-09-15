"use client"

import { Loader2 } from "lucide-react"

import { useFrontPhotoUrl } from "@/hooks/useFrontPhotoUrl"
import type { ReportOut } from "@/lib/reports/reportApi"

const ANALYSIS_POINTS = [
  "Measured morphology from your photos",
  "Projected potential by feature",
  "Tiered treatment recommendations",
] as const

/**
 * Left-column “Your Facial Analysis” card -- reuses report teaser intro
 * and the validated front photo. Numbered points describe FaceIQ’s real
 * pipeline stages (no invented clinical claims).
 */
export function FacialAnalysisIntroCard({ report }: { report: ReportOut }) {
  const frontPhotoUrl = useFrontPhotoUrl()
  const intro = report.teaser.intro

  return (
    <div className="flex h-fit w-full flex-col gap-4 rounded-2xl border border-border/80 bg-card p-5 shadow-[0_10px_30px_-18px_rgba(20,55,75,0.28)]">
      <div>
        <h2 className="font-heading text-lg font-semibold tracking-tight text-primary">
          Your <span className="text-foreground">Facial Analysis</span>
        </h2>
        {intro ? (
          <p className="mt-2 line-clamp-4 text-sm leading-relaxed text-muted-foreground">{intro}</p>
        ) : (
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            A structured review of facial proportions, feature scores, and recommended next steps.
          </p>
        )}
      </div>

      <div className="overflow-hidden rounded-xl bg-muted/40">
        {frontPhotoUrl ? (
          // eslint-disable-next-line @next/next/no-img-element -- authenticated blob URL
          <img
            src={frontPhotoUrl}
            alt="Your validated front photo"
            className="mx-auto block h-36 w-full max-w-[12rem] object-cover"
          />
        ) : (
          <div className="flex h-36 items-center justify-center">
            <Loader2 className="size-5 animate-spin text-muted-foreground/60" aria-hidden />
          </div>
        )}
      </div>

      <ol className="space-y-2 text-sm text-muted-foreground">
        {ANALYSIS_POINTS.map((point, index) => (
          <li key={point} className="flex gap-2.5">
            <span className="font-semibold text-primary tabular-nums">{index + 1}.</span>
            <span>{point}</span>
          </li>
        ))}
      </ol>
    </div>
  )
}
