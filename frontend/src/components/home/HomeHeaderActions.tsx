"use client"

import { Download, Loader2 } from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"

import { getErrorMessage } from "@/lib/api/getErrorMessage"
import { formatDate } from "@/lib/format"
import { downloadReportPdf } from "@/lib/reports/downloadReportPdf"
import type { ReportOut } from "@/lib/reports/reportApi"

/**
 * Home Overview header row (spec §1.1) -- breadcrumb-style meta
 * [Recommendation, layout only] + Download PDF (reuses GET /reports/{id}/pdf,
 * same as AppNavbar's PDF button and /report's own download button). No
 * Share button: not implemented in FaceIQ scope yet, so nothing is shipped
 * rather than a dead/disabled control (spec §1.1's explicit instruction).
 */
export function HomeHeaderActions({ report }: { report: ReportOut }) {
  const [isDownloading, setIsDownloading] = useState(false)

  async function handleDownload() {
    setIsDownloading(true)
    try {
      await downloadReportPdf(report.id, report.created_at)
      toast.success("Report downloaded.")
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setIsDownloading(false)
    }
  }

  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      {/* Breadcrumb-style meta [Recommendation -- layout only, spec §1.1].
          No "Protocol #..." number: no such field exists in the data model,
          and the user's own name already shows in the header's profile
          pill -- repeating it here would just duplicate UserMenu. */}
      <p className="text-sm text-muted-foreground">Your Facial Aanlysis Report · Generated {formatDate(report.created_at)}</p>
      <button
        type="button"
        onClick={() => void handleDownload()}
        disabled={isDownloading}
        className="inline-flex h-9 items-center gap-1.5 rounded-full border border-border/80 bg-card px-3.5 text-sm font-medium text-foreground transition hover:bg-muted/80 disabled:pointer-events-none disabled:opacity-60"
      >
        {isDownloading ? <Loader2 className="size-3.5 animate-spin" /> : <Download className="size-3.5" aria-hidden />}
        Download PDF
      </button>
    </div>
  )
}
