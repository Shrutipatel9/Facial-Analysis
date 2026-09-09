"use client"

import { Download, FileText, Loader2 } from "lucide-react"
import Link from "next/link"
import { useEffect, useState } from "react"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { getErrorMessage } from "@/lib/api/getErrorMessage"
import { formatDate } from "@/lib/format"
import { downloadReportPdf } from "@/lib/reports/downloadReportPdf"
import * as reportApi from "@/lib/reports/reportApi"
import type { ReportSummary } from "@/lib/reports/reportApi"

export function ReportSummaryCard() {
  const [report, setReport] = useState<ReportSummary | null | undefined>(undefined)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isDownloading, setIsDownloading] = useState(false)

  useEffect(() => {
    let cancelled = false
    reportApi
      .listReports()
      .then((reports) => {
        if (!cancelled) setReport(reports[0] ?? null)
      })
      .catch((err) => {
        if (!cancelled) setErrorMessage(getErrorMessage(err))
      })
    return () => {
      cancelled = true
    }
  }, [])

  async function handleDownload() {
    if (!report) return
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
    <div className="flex flex-col gap-4 rounded-2xl border border-border bg-card p-6">
      <div className="flex items-center gap-2.5">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
          <FileText className="size-4" />
        </span>
        <h2 className="font-heading text-lg font-semibold tracking-tight">Your report</h2>
      </div>

      {errorMessage ? (
        <p className="text-sm text-destructive">{errorMessage}</p>
      ) : report === undefined ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="size-5 animate-spin text-primary/50" aria-label="Loading" />
        </div>
      ) : report === null ? (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">Your report hasn&apos;t been generated yet.</p>
          <Button className="h-10 rounded-full" render={<Link href="/report" />} nativeButton={false}>
            View your report
          </Button>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Badge variant="default">{report.publish_state}</Badge>
            <span className="text-sm text-muted-foreground">Generated {formatDate(report.created_at)}</span>
          </div>
          <div className="flex flex-wrap gap-2.5">
            <Button
              variant="outline"
              className="h-10 rounded-full"
              render={<Link href="/report" />}
              nativeButton={false}
            >
              View report
            </Button>
            <Button className="h-10 rounded-full" onClick={handleDownload} disabled={isDownloading}>
              {isDownloading ? <Loader2 className="size-4 animate-spin" /> : <Download className="size-4" />}
              Download PDF
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
