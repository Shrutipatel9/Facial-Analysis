"use client"

import { motion } from "motion/react"

import { BeforeAfterBlock } from "../ui/BeforeAfterBlock"
import { FeatureMetricsBlock } from "../ui/FeatureMetricsBlock"
import { HairLossScale } from "../ui/HairLossScale"
import { meridian } from "@/lib/report/meridianTokens"
import { humanizeMetricKey } from "@/lib/report/metricLabels"
import { FEATURE_LABELS, featureAnchorId } from "@/lib/report/reportFeatures"
import type { HairLoss, ReportFeatureSection } from "@/lib/reports/reportApi"

export function FeatureSection({
  reportId,
  feature,
  data,
  visualStatus,
  imageUrl,
  animationDelay,
  hairLoss = null,
}: {
  reportId: string
  feature: string
  data: ReportFeatureSection
  visualStatus: string
  imageUrl: string | undefined
  animationDelay: number
  /** report_design_spec.md v3.0 §13.3 -- only ever passed for the "hair" feature; null elsewhere or when not assessable. */
  hairLoss?: HairLoss | null
}) {
  const label = FEATURE_LABELS[feature]
  const labelLower = label.toLowerCase()
  // Fallback for the header when summary_callout is unexpectedly empty --
  // summary_callout is always populated in practice (see
  // report_assembly_service.py's templated fallback), so this branch is
  // rarely hit either way.
  const firstSectionContent = Object.values(data.sections)[0] ?? ""

  return (
    <motion.div
      id={featureAnchorId(feature)}
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: animationDelay, ease: "easeOut" }}
      className="scroll-mt-8 space-y-5 border-b border-border/60 pb-10 last:border-b-0"
    >
      <header className="space-y-1.5">
        <h2 className="text-2xl font-semibold tracking-tight text-foreground sm:text-[1.75rem]">
          Summary of your{" "}
          <span style={{ color: meridian.accent.secondary }}>{labelLower}</span>
        </h2>
        {data.summary_callout ? (
          <p className="text-sm leading-relaxed" style={{ color: meridian.ink.muted }}>
            {data.summary_callout}
          </p>
        ) : (
          <p className="text-sm leading-relaxed" style={{ color: meridian.ink.muted }}>
            {firstSectionContent.slice(0, 160)}
            {firstSectionContent.length > 160 ? "…" : ""}
          </p>
        )}
      </header>

      {imageUrl ? (
        // eslint-disable-next-line @next/next/no-img-element -- authenticated blob URL, next/image can't proxy this
        <img
          src={imageUrl}
          alt={`${label} detail from your uploaded photo`}
          className="h-40 w-auto max-w-full rounded-xl object-contain"
        />
      ) : null}

      <div className="space-y-2">
        <h3 className="text-sm font-semibold tracking-tight" style={{ color: meridian.ink.primary }}>
          Summary of your {labelLower}
        </h3>
        <FeatureMetricsBlock measurement={data.measurement} />
      </div>

      {Object.keys(data.attributes).length > 0 ? (
        <div className="flex flex-wrap gap-1.5">
          {Object.entries(data.attributes).map(([key, value]) => (
            <span
              key={key}
              className="rounded-full px-2.5 py-1 text-xs"
              style={{ backgroundColor: meridian.surface.recessed, color: meridian.ink.primary }}
            >
              <span style={{ color: meridian.ink.muted }}>{humanizeMetricKey(key)}:</span> {value}
            </span>
          ))}
        </div>
      ) : null}

      <div className="space-y-4">
        {Object.entries(data.sections).map(([heading, content]) => (
          <div key={heading} className="space-y-1.5">
            <h3 className="text-sm font-semibold tracking-tight" style={{ color: meridian.ink.primary }}>
              {heading}
            </h3>
            <p className="text-sm leading-relaxed" style={{ color: meridian.ink.muted }}>
              {content}
            </p>
            {/* The illustrated stage scale sits inside the "Hair Loss" sub-section, right after its
                own prose -- matching report_pdf_service.py's same interleaving in the PDF. */}
            {feature === "hair" && heading === "Hair Loss" && hairLoss ? (
              <HairLossScale stage={hairLoss.stage} label={hairLoss.label} />
            ) : null}
          </div>
        ))}
        {data.strengths ? (
          <p className="text-sm leading-relaxed" style={{ color: meridian.ink.muted }}>
            <span className="font-medium" style={{ color: meridian.ink.primary }}>
              Strengths:{" "}
            </span>
            {data.strengths}
          </p>
        ) : null}
        {data.areas_of_note ? (
          <p className="text-sm leading-relaxed" style={{ color: meridian.ink.muted }}>
            <span className="font-medium" style={{ color: meridian.ink.primary }}>
              Areas of note:{" "}
            </span>
            {data.areas_of_note}
          </p>
        ) : null}
      </div>

      {data.projected_potential.length > 0 ? (
        <ul className="space-y-1 pl-1 text-sm" style={{ color: meridian.ink.muted }}>
          {data.projected_potential.map((idea) => (
            <li key={idea} className="flex gap-2">
              <span style={{ color: meridian.accent.primary }}>•</span>
              <span>{idea}</span>
            </li>
          ))}
        </ul>
      ) : null}

      <BeforeAfterBlock
        reportId={reportId}
        feature={feature}
        featureLabel={label}
        visualStatus={visualStatus}
        beforeImageUrl={imageUrl}
      />
    </motion.div>
  )
}
