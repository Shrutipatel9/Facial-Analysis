"use client"

import { AlertCircle, Loader2 } from "lucide-react"
import { useRouter } from "next/navigation"
import { useEffect, useRef, useState } from "react"

import { BeforePotentialPair } from "./BeforePotentialPair"
import { FacialAgeCard } from "./FacialAgeCard"
import { FacialAnalysisIntroCard } from "./FacialAnalysisIntroCard"
import { HarmonyOverviewSection } from "./HarmonyOverviewSection"
import { HomeHeaderActions } from "./HomeHeaderActions"
import { PriorityFeaturesCard } from "./PriorityFeaturesCard"
import { ProtocolEntryCard } from "./ProtocolEntryCard"
import { StatRow } from "./StatRow"
import { TreatmentProtocolPanel } from "./TreatmentProtocolPanel"
import { Button } from "@/components/ui/button"
import { ApiError } from "@/lib/api/errors"
import { getErrorMessage } from "@/lib/api/getErrorMessage"
import * as reportApi from "@/lib/reports/reportApi"
import { useReportStore } from "@/store/reportStore"

/**
 * Home Overview -- post-analysis landing (spec §1):
 * stats row + left stack (protocol/photos + priority + feature evaluation)
 * with Treatment Protocol as the full right column.
 */
export function HomeOverviewScreen() {
  const router = useRouter()
  const report = useReportStore((state) => state.report)
  const setReport = useReportStore((state) => state.setReport)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const hasFetched = useRef(false)

  useEffect(() => {
    if (report !== null || hasFetched.current) return
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
          setErrorMessage("Your analysis isn't complete yet. Head back to finish it first.")
        } else {
          setErrorMessage(getErrorMessage(err))
        }
      }
    }
    void load()
  }, [report, setReport])

  if (report === null && errorMessage === null) {
    return (
      <div className="flex h-full min-h-0 flex-1 flex-col items-center justify-center gap-4 px-6 py-16 text-center">
        <Loader2 className="size-8 animate-spin text-primary" aria-hidden />
        <p className="text-base text-muted-foreground">Preparing your overview…</p>
      </div>
    )
  }

  if (errorMessage || !report) {
    return (
      <div className="flex h-full min-h-0 flex-1 flex-col items-center justify-center gap-4 px-6 py-16 text-center">
        <span className="flex size-14 items-center justify-center rounded-full bg-destructive/10 text-destructive">
          <AlertCircle className="size-6" />
        </span>
        <h1 className="font-sans text-2xl font-semibold tracking-tight">Overview not available</h1>
        <p className="max-w-md text-base leading-relaxed text-muted-foreground">
          {errorMessage ?? "Something went wrong while loading your overview."}
        </p>
        <Button type="button" variant="outline" className="h-10 rounded-full px-6" onClick={() => router.push("/home")}>
          Try again
        </Button>
      </div>
    )
  }

  return (
    <div className="flex h-full min-h-0 w-full flex-1 flex-col overflow-hidden bg-[#eef1f3] px-5 py-4 sm:px-8 sm:py-5 lg:px-10 lg:py-6">
      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain rounded-2xl border border-black/[0.06] bg-[#f4f6f7] px-5 py-5 shadow-[0_1px_2px_rgba(0,0,0,0.04)] sm:px-7 sm:py-6 lg:px-8 lg:py-7">
        <div className="w-full space-y-5">
          <HomeHeaderActions report={report} />
          <StatRow report={report} />

          {/* Left 2/3: protocol + photos + priority + feature evaluation
              Right 1/3: treatment protocol full column */}
          <div className="grid grid-cols-1 items-start gap-4 xl:grid-cols-[minmax(0,2.15fr)_minmax(17rem,1fr)]">
            <div className="flex min-w-0 flex-col gap-4">
              <div className="grid grid-cols-1 items-start gap-4 md:grid-cols-[minmax(14rem,0.85fr)_minmax(0,1.25fr)]">
                <div className="flex flex-col gap-4">
                  <ProtocolEntryCard report={report} />
                  <FacialAnalysisIntroCard report={report} />
                </div>
                <div className="flex flex-col gap-4">
                  <BeforePotentialPair />
                  {report.full.facial_age ? <FacialAgeCard facialAge={report.full.facial_age} /> : null}
                </div>
              </div>

              <PriorityFeaturesCard featureScores={report.full.feature_scores} />
              <HarmonyOverviewSection report={report} />
            </div>

            <div className="xl:sticky xl:top-4">
              <TreatmentProtocolPanel full={report.full} />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
