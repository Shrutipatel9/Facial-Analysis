"use client"

import {
  AlertCircle,
  ChevronDown,
  CircleDot,
  Download,
  Droplet,
  Ear,
  Eye,
  Loader2,
  Minus,
  MoveVertical,
  Scissors,
  Smile,
  Square,
  Wind,
} from "lucide-react"
import { motion } from "motion/react"
import { useRouter } from "next/navigation"
import { useEffect, useRef, useState } from "react"
import { toast } from "sonner"
import type { LucideIcon } from "lucide-react"

import { FacialScanVisual } from "@/components/auth/FacialScanVisual"
import { Button } from "@/components/ui/button"
import { ApiError } from "@/lib/api/errors"
import { getErrorMessage } from "@/lib/api/getErrorMessage"
import * as reportApi from "@/lib/reports/reportApi"
import type { ReportOut } from "@/lib/reports/reportApi"
import { downloadReportPdf } from "@/lib/reports/downloadReportPdf"
import { useReportStore } from "@/store/reportStore"

/**
 * Meridian-inspired report visual language (see docs/report_design_spec.md,
 * docs/report_template.md), applied narrowly to report cards — not as a
 * full-page yellow paper wash. Outer shell matches the app's soft teal-neutral
 * surface; only card tokens below stay Meridian.
 */
const MERIDIAN = {
  card: "#FFFFFF",
  ink: "#2B2822",
  inkMuted: "#6B6558",
  accent: "#A8461F",
  accentSecondary: "#3E6E64",
  recessed: "#EFEAE0",
}

// Fixed, verbatim order from FR-009/BR-008 -- mirrors
// Backend/app/services/facial_measurement_service.py's ANALYSIS_FEATURES.
const FEATURE_ORDER = [
  "hair",
  "eyebrows",
  "eyes",
  "nose",
  "cheeks",
  "jaw",
  "lips",
  "chin",
  "skin",
  "neck",
  "ears",
] as const

const FEATURE_LABELS: Record<string, string> = {
  hair: "Hair",
  eyebrows: "Eyebrows",
  eyes: "Eyes",
  nose: "Nose",
  cheeks: "Cheeks",
  jaw: "Jaw",
  lips: "Lips",
  chin: "Chin",
  skin: "Skin",
  neck: "Neck",
  ears: "Ears",
}

// One icon per feature, from a single library (Meridian §1.4's rule),
// never decorative -- always the same feature/icon pairing.
const FEATURE_ICONS: Record<string, LucideIcon> = {
  hair: Scissors,
  eyebrows: Minus,
  eyes: Eye,
  nose: Wind,
  cheeks: CircleDot,
  jaw: Square,
  lips: Smile,
  chin: ChevronDown,
  skin: Droplet,
  neck: MoveVertical,
  ears: Ear,
}

/**
 * Reached via a link from /dashboard, not the forced onboarding-guard chain
 * -- see D:\zzz\report-generation\plans.md. Lazily generates the report on
 * first visit (POST /reports is idempotent get-or-create, fast/synchronous,
 * no AI call -- see report_service.get_or_create_report), then renders it.
 * Always fully populated: payment gates the START of analysis itself
 * (D:\zzz\payment\plans.md), so a Report can only ever exist already paid.
 *
 * Layout: left scan visual stays fixed; right column alone scrolls.
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

  let rightPane: React.ReactNode

  if (isLoading) {
    rightPane = (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 px-6 py-16 text-center">
        <Loader2 className="size-8 animate-spin text-primary" aria-hidden />
        <p className="text-base text-muted-foreground">Preparing your report…</p>
      </div>
    )
  } else if (errorMessage || !report) {
    rightPane = (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 px-6 py-16 text-center">
        <span className="flex size-14 items-center justify-center rounded-full bg-destructive/10 text-destructive">
          <AlertCircle className="size-6" />
        </span>
        <h1 className="font-sans text-2xl font-semibold tracking-tight">Report not available</h1>
        <p className="max-w-md text-base leading-relaxed text-muted-foreground">
          {errorMessage ?? "Something went wrong while loading your report."}
        </p>
        <Button type="button" variant="outline" className="h-10 rounded-full px-6" onClick={() => router.push("/dashboard")}>
          Back to dashboard
        </Button>
      </div>
    )
  } else {
    rightPane = (
      <ReportContent
        report={report}
        isDownloading={isDownloading}
        onDownload={() => void handleDownload(report.id, report.created_at)}
      />
    )
  }

  return (
    <section className="grid h-full min-h-0 flex-1 overflow-hidden lg:grid-cols-[minmax(16rem,0.85fr)_minmax(0,1.35fr)]">
      <aside className="relative hidden min-h-0 flex-col items-center justify-center gap-8 overflow-hidden px-8 py-10 lg:flex">
        <motion.div
          className="absolute inset-[14%] rounded-full bg-primary/[0.07] blur-3xl"
          animate={{ scale: [1, 1.05, 1], opacity: [0.45, 0.8, 0.45] }}
          transition={{ duration: 7, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          initial={{ opacity: 0.7, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.35 }}
          className="relative"
        >
          <FacialScanVisual className="h-[min(56vh,400px)] w-auto" tone="onLight" />
        </motion.div>
      </aside>

      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto overscroll-contain px-5 py-6 sm:px-8 lg:px-10 lg:py-8">
        {rightPane}
      </div>
    </section>
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
    <div className="mx-auto w-full max-w-3xl space-y-4 pb-10">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className="space-y-4 rounded-2xl p-7 shadow-sm"
        style={{ backgroundColor: MERIDIAN.card }}
      >
        <div>
          <p className="text-xs font-medium tracking-[0.18em] uppercase" style={{ color: MERIDIAN.accentSecondary }}>
            Facial Analysis Report
          </p>
          <div className="mt-2 h-px w-10" style={{ backgroundColor: MERIDIAN.accent }} />
        </div>
        <p className="text-sm leading-relaxed" style={{ color: MERIDIAN.inkMuted }}>
          {report.teaser.intro}
        </p>
        <Button type="button" className="h-10 rounded-full px-5" onClick={onDownload} disabled={isDownloading}>
          {isDownloading ? <Loader2 className="size-4 animate-spin" /> : <Download />}
          Download PDF
        </Button>
      </motion.div>

      <div className="space-y-2.5">
        {FEATURE_ORDER.map((feature, index) => {
          const data = full.features[feature]
          if (!data) return null
          const Icon = FEATURE_ICONS[feature]
          const imageUrl = images[feature]
          return (
            <motion.div
              key={feature}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: Math.min(index * 0.025, 0.25), ease: "easeOut" }}
              className="space-y-3 rounded-2xl p-5 shadow-sm"
              style={{ backgroundColor: MERIDIAN.card }}
            >
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <span
                    className="flex size-8 shrink-0 items-center justify-center rounded-full"
                    style={{ backgroundColor: MERIDIAN.recessed, color: MERIDIAN.accentSecondary }}
                  >
                    <Icon className="size-4" aria-hidden />
                  </span>
                  <h2 className="text-[15px] font-semibold tracking-tight" style={{ color: MERIDIAN.ink }}>
                    {FEATURE_LABELS[feature]}
                  </h2>
                </div>
                <span
                  className="shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium"
                  style={{
                    backgroundColor: data.measurement.available ? undefined : MERIDIAN.recessed,
                    color: data.measurement.available ? MERIDIAN.accent : MERIDIAN.inkMuted,
                  }}
                >
                  {data.measurement.available ? "Measured" : "AI-assessed"}
                </span>
              </div>

              {imageUrl ? (
                // eslint-disable-next-line @next/next/no-img-element -- authenticated blob URL, next/image can't proxy this
                <img
                  src={imageUrl}
                  alt={`${FEATURE_LABELS[feature]} detail from your uploaded photo`}
                  className="max-h-40 w-auto rounded-lg object-cover"
                />
              ) : null}

              {data.summary_callout ? (
                <p className="text-sm font-medium" style={{ color: MERIDIAN.accentSecondary }}>
                  {data.summary_callout}
                </p>
              ) : null}

              <div className="space-y-2 text-sm leading-relaxed" style={{ color: MERIDIAN.inkMuted }}>
                <p>{data.narrative}</p>
                {data.strengths ? (
                  <p>
                    <span className="font-medium" style={{ color: MERIDIAN.ink }}>
                      Strengths:{" "}
                    </span>
                    {data.strengths}
                  </p>
                ) : null}
                {data.areas_of_note ? (
                  <p>
                    <span className="font-medium" style={{ color: MERIDIAN.ink }}>
                      Areas of note:{" "}
                    </span>
                    {data.areas_of_note}
                  </p>
                ) : null}
              </div>

              {data.projected_potential.length > 0 ? (
                <ul className="space-y-1 pl-1 text-sm" style={{ color: MERIDIAN.inkMuted }}>
                  {data.projected_potential.map((idea) => (
                    <li key={idea} className="flex gap-2">
                      <span style={{ color: MERIDIAN.accent }}>•</span>
                      <span>{idea}</span>
                    </li>
                  ))}
                </ul>
              ) : null}
            </motion.div>
          )
        })}
      </div>

      <div className="rounded-2xl p-6 shadow-sm" style={{ backgroundColor: MERIDIAN.recessed }}>
        <h3 className="text-xs font-semibold tracking-[0.1em] uppercase" style={{ color: MERIDIAN.ink }}>
          Disclaimer
        </h3>
        <p className="mt-2 text-xs leading-relaxed" style={{ color: MERIDIAN.inkMuted }}>
          {full.limitations}
        </p>
      </div>
    </div>
  )
}
