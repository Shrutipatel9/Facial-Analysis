"use client"

import { AlertCircle, Loader2 } from "lucide-react"
import { useRouter } from "next/navigation"
import { useEffect, useRef, useState } from "react"
import { toast } from "sonner"

import { ReportLayout } from "./ReportLayout"
import { FacialAssessmentsSection } from "./sections/FacialAssessmentsSection"
import { FeatureSection } from "./sections/FeatureSection"
import { IntroductionSection } from "./sections/IntroductionSection"
import { ProtocolSection } from "./sections/ProtocolSection"
import { Button } from "@/components/ui/button"
import { ApiError } from "@/lib/api/errors"
import { getErrorMessage } from "@/lib/api/getErrorMessage"
import { downloadReportPdf } from "@/lib/reports/downloadReportPdf"
import * as reportApi from "@/lib/reports/reportApi"
import type { ReportOut } from "@/lib/reports/reportApi"
import { FEATURE_ORDER } from "@/lib/report/reportFeatures"
import { useReportStore } from "@/store/reportStore"

const VISUALS_POLL_INTERVAL_MS = 3000

/**
 * Reached via the persistent header nav's "Report" link (AppNavbar) or Home
 * Overview's "View Full Report" CTA, not the forced onboarding-guard chain
 * -- see D:\zzz\report-generation\plans.md. Lazily generates the report on
 * first visit (POST /reports is idempotent get-or-create, fast/synchronous,
 * no AI call -- see report_service.get_or_create_report), then renders it.
 * Always fully populated: payment gates the START of analysis itself
 * (D:\zzz\payment\plans.md), so a Report can only ever exist already paid.
 */
export function ReportScreen() {
  const router = useRouter()
  const report = useReportStore((state) => state.report)
  const setReport = useReportStore((state) => state.setReport)
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isDownloading, setIsDownloading] = useState(false)
  const hasFetched = useRef(false)

  useEffect(() => {
    if (hasFetched.current) return
    hasFetched.current = true

    async function load() {
      try {
        const existing = await reportApi.listReports()
        if (existing.length > 0) {
          const full = await reportApi.getReport(existing[0].id)
          setReport(full)
        } else {
          const created = await reportApi.generateReport()
          setReport(created)
        }
      } catch (err) {
        if (err instanceof ApiError && err.code === "ANALYSIS_NOT_COMPLETED") {
          setErrorMessage("Your analysis isn't complete yet. Head back to your dashboard to finish it first.")
        } else {
          setErrorMessage(getErrorMessage(err))
        }
      } finally {
        setIsLoading(false)
      }
    }
    void load()
  }, [setReport])

  async function handleDownload(reportId: string, createdAt: string) {
    setIsDownloading(true)
    try {
      await downloadReportPdf(reportId, createdAt)
      toast.success("Report downloaded.")
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setIsDownloading(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex h-full min-h-0 flex-1 flex-col items-center justify-center gap-4 px-6 py-16 text-center">
        <Loader2 className="size-8 animate-spin text-primary" aria-hidden />
        <p className="text-base text-muted-foreground">Preparing your report…</p>
      </div>
    )
  }

  if (errorMessage || !report) {
    return (
      <div className="flex h-full min-h-0 flex-1 flex-col items-center justify-center gap-4 px-6 py-16 text-center">
        <span className="flex size-14 items-center justify-center rounded-full bg-destructive/10 text-destructive">
          <AlertCircle className="size-6" />
        </span>
        <h1 className="font-sans text-2xl font-semibold tracking-tight">Report not available</h1>
        <p className="max-w-md text-base leading-relaxed text-muted-foreground">
          {errorMessage ?? "Something went wrong while loading your report."}
        </p>
        <Button type="button" variant="outline" className="h-10 rounded-full px-6" onClick={() => router.push("/report")}>
          Try again
        </Button>
      </div>
    )
  }

  return (
    <ReportLayout>
      <ReportContent
        report={report}
        isDownloading={isDownloading}
        onDownload={() => void handleDownload(report.id, report.created_at)}
      />
    </ReportLayout>
  )
}

function ReportContent({
  report,
  isDownloading,
  onDownload,
}: {
  report: ReportOut
  isDownloading: boolean
  onDownload: () => void
}) {
  const full = report.full
  const [images, setImages] = useState<Record<string, string>>({})
  const imagesFetchedFor = useRef<string | null>(null)
  // Milestone 2 (FR-022): `full.features[feature].visual_status` is a
  // snapshot taken when `report` was last fetched -- report_service's
  // per-feature visual generation is a background task that finishes well
  // after that snapshot, and nothing re-fetches the whole report to pick up
  // the change. Without live polling here, a feature stuck on "pending" at
  // page-load renders BeforeAfterBlock's "generating" message forever, even
  // once the backend row has long since settled to "generated"/"failed".
  // Same POLL_INTERVAL_MS convention as ai-visuals/HairstyleView.tsx.
  const [visualsStatus, setVisualsStatus] = useState<Record<string, string> | null>(null)

  useEffect(() => {
    let cancelled = false
    let timer: ReturnType<typeof setInterval> | null = null

    async function poll() {
      try {
        const result = await reportApi.getVisualsStatus(report.id)
        if (cancelled) return
        setVisualsStatus(result)
        const stillInFlight = Object.values(result).some((status) => status === "pending" || status === "generating")
        if (!stillInFlight && timer) {
          clearInterval(timer)
          timer = null
        }
      } catch {
        // Transient network errors: keep polling silently, same posture as
        // HairstyleView.tsx's own poll catch.
      }
    }

    void poll()
    timer = setInterval(poll, VISUALS_POLL_INTERVAL_MS)
    return () => {
      cancelled = true
      if (timer) clearInterval(timer)
    }
  }, [report.id])

  useEffect(() => {
    if (imagesFetchedFor.current === report.id) return
    imagesFetchedFor.current = report.id

    const featuresWithImages = FEATURE_ORDER.filter((feature) => full.features[feature]?.has_image)
    Promise.all(
      featuresWithImages.map(async (feature) => {
        try {
          const blob = await reportApi.getFeatureImage(report.id, feature)
          return [feature, URL.createObjectURL(blob)] as const
        } catch {
          return null
        }
      })
    ).then((results) => {
      const next: Record<string, string> = {}
      for (const result of results) {
        if (result) next[result[0]] = result[1]
      }
      setImages(next)
    })

    // Object URLs are revoked when the component unmounts (e.g. navigating away).
    return () => {
      setImages((current) => {
        Object.values(current).forEach((url) => URL.revokeObjectURL(url))
        return current
      })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- full.features is derived from report, keyed by report.id above
  }, [report.id])

  return (
    <div className="mx-auto w-full max-w-3xl space-y-8 pb-6">
      <IntroductionSection report={report} isDownloading={isDownloading} onDownload={onDownload} />

      <FacialAssessmentsSection full={full} />

      <div className="space-y-2.5">
        <h2 className="px-1 text-xs font-semibold tracking-[0.14em] uppercase text-muted-foreground">
          Features Analysis
        </h2>
        <div className="space-y-2.5">
          {FEATURE_ORDER.map((feature, index) => {
            const data = full.features[feature]
            if (!data) return null
            return (
              <FeatureSection
                key={feature}
                reportId={report.id}
                feature={feature}
                data={data}
                visualStatus={visualsStatus?.[feature] ?? data.visual_status}
                imageUrl={images[feature]}
                animationDelay={Math.min(index * 0.025, 0.25)}
                hairLoss={feature === "hair" ? full.hair_loss : null}
              />
            )
          })}
        </div>
      </div>

      <ProtocolSection full={full} />
    </div>
  )
}
