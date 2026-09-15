"use client"

import { motion } from "motion/react"

import { ScoreSlider } from "../../ui/ScoreSlider"
import { meridian } from "@/lib/report/meridianTokens"
import { assessmentAnchorId } from "@/lib/report/reportFeatures"
import type { FacialAssessment } from "@/lib/reports/reportApi"

/**
 * Shared card shell for all 5 Facial Assessments pages: title + score +
 * label + slider, or the unavailable-state note. `children` carries each
 * page's own content (driver lists, overlays, grids) rendered below.
 */
export function AssessmentOverviewCard({
  id,
  title,
  data,
  sliderLeftLabel,
  sliderRightLabel,
  children,
}: {
  id: string
  title: string
  data: FacialAssessment
  /** Axis endpoint captions for the score slider (spec §2.2, e.g. "Hyper
   * Feminine" / "Hyper Masculine") -- static UI copy describing what the
   * axis represents, not a data value. */
  sliderLeftLabel?: string
  sliderRightLabel?: string
  children?: React.ReactNode
}) {
  return (
    <motion.div
      id={assessmentAnchorId(id)}
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className="scroll-mt-24 space-y-3 rounded-2xl p-5 shadow-sm"
      style={{ backgroundColor: meridian.surface.card }}
    >
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-[15px] font-semibold tracking-tight" style={{ color: meridian.ink.primary }}>
          {title}
        </h2>
        {data.available && data.score !== null ? (
          <span className="text-lg font-semibold tabular-nums" style={{ color: meridian.accent.primary }}>
            {Math.round(data.score)}
            <span className="text-xs font-normal" style={{ color: meridian.ink.muted }}>
              /100
            </span>
          </span>
        ) : null}
      </div>

      {data.available ? (
        <>
          {data.label ? (
            <p className="text-sm font-medium" style={{ color: meridian.accent.secondary }}>
              {data.label}
            </p>
          ) : null}
          {data.score !== null ? (
            <ScoreSlider value={data.score} leftLabel={sliderLeftLabel} rightLabel={sliderRightLabel} />
          ) : null}
          {data.note ? (
            <p className="text-xs leading-relaxed" style={{ color: meridian.ink.muted }}>
              {data.note}
            </p>
          ) : null}
          {children}
        </>
      ) : (
        <p className="text-sm" style={{ color: meridian.ink.muted }}>
          {data.note ?? "Not available for this report."}
        </p>
      )}
    </motion.div>
  )
}
