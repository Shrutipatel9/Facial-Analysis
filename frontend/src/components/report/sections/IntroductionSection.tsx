"use client"

import { Download, Loader2 } from "lucide-react"
import { motion } from "motion/react"

import { Button } from "@/components/ui/button"
import { meridian } from "@/lib/report/meridianTokens"
import type { ReportOut } from "@/lib/reports/reportApi"

export function IntroductionSection({
  report,
  isDownloading,
  onDownload,
}: {
  report: ReportOut
  isDownloading: boolean
  onDownload: () => void
}) {
  return (
    <motion.div
      id="introduction"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="scroll-mt-24 space-y-4 rounded-2xl p-7 shadow-sm"
      style={{ backgroundColor: meridian.surface.card }}
    >
      <div>
        <p className="text-xs font-medium tracking-[0.18em] uppercase" style={{ color: meridian.accent.secondary }}>
          Facial Analysis Report
        </p>
        <div className="mt-2 h-px w-10" style={{ backgroundColor: meridian.accent.primary }} />
      </div>
      <p className="text-sm leading-relaxed" style={{ color: meridian.ink.muted }}>
        {report.teaser.intro}
      </p>
      {report.full.understanding_your_results ? (
        <p
          id="disclaimer"
          className="scroll-mt-24 text-sm leading-relaxed"
          style={{ color: meridian.ink.muted }}
        >
          {report.full.understanding_your_results}
        </p>
      ) : (
        <p
          id="disclaimer"
          className="scroll-mt-24 text-sm leading-relaxed"
          style={{ color: meridian.ink.muted }}
        >
          This report is informational only and is not medical, clinical, or treatment advice. Consult a
          qualified professional before making decisions about your appearance or health.
        </p>
      )}
      <Button type="button" className="h-10 rounded-full px-5" onClick={onDownload} disabled={isDownloading}>
        {isDownloading ? <Loader2 className="size-4 animate-spin" /> : <Download />}
        Download PDF
      </Button>
    </motion.div>
  )
}
