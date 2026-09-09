"use client"

import { LayoutDashboard } from "lucide-react"
import { motion } from "motion/react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { useEffect } from "react"

import { BrandLoader } from "@/components/branding/BrandLoader"
import { Logo } from "@/components/branding/Logo"
import { UserMenu } from "@/components/layout/UserMenu"
import { Button } from "@/components/ui/button"
import { useAnalysisGuard } from "@/hooks/useAnalysisGuard"
import { useAuthGuard } from "@/hooks/useAuthGuard"
import { useOnboardingEntryGuard } from "@/hooks/useOnboardingEntryGuard"
import { usePaymentGuard } from "@/hooks/usePaymentGuard"
import { usePhotoUploadGuard } from "@/hooks/usePhotoUploadGuard"
import { useQuestionnaireGuard } from "@/hooks/useQuestionnaireGuard"
import * as reportApi from "@/lib/reports/reportApi"
import { cn } from "@/lib/utils"
import { useReportStore } from "@/store/reportStore"

const FULL_BLEED = new Set(["/questionnaire", "/photos", "/payment", "/analysis", "/report"])
const INNER_SCROLL = new Set(["/report"])

export default function ProtectedRouteGroupLayout({ children }: { children: React.ReactNode }) {
  const { isChecking: isAuthChecking } = useAuthGuard()
  const { isChecking: isQuestionnaireChecking } = useQuestionnaireGuard(!isAuthChecking)
  const { isChecking: isPhotoChecking } = usePhotoUploadGuard(!isAuthChecking && !isQuestionnaireChecking)
  const { isChecking: isPaymentChecking } = usePaymentGuard(
    !isAuthChecking && !isQuestionnaireChecking && !isPhotoChecking
  )
  const { isChecking: isAnalysisChecking } = useAnalysisGuard(
    !isAuthChecking && !isQuestionnaireChecking && !isPhotoChecking && !isPaymentChecking
  )
  const isChecking =
    isAuthChecking || isQuestionnaireChecking || isPhotoChecking || isPaymentChecking || isAnalysisChecking
  // Single, centralized redirect decision for an incomplete user landing on
  // /dashboard -- see useOnboardingEntryGuard's docstring for why this
  // can't be three independent per-step effects.
  useOnboardingEntryGuard(!isAuthChecking)
  const pathname = usePathname()
  const isFullBleed = FULL_BLEED.has(pathname)
  // Report owns its own right-pane scroll so the scan logo stays fixed.
  const usesInnerScroll = INNER_SCROLL.has(pathname)
  const hasReport = useReportStore((state) => state.hasReport)
  const setHasReport = useReportStore((state) => state.setHasReport)

  // Dashboard nav only after at least one report exists (FR-017 workspace).
  useEffect(() => {
    if (isChecking || hasReport !== null) return
    let cancelled = false
    reportApi
      .listReports()
      .then((reports) => {
        if (!cancelled) setHasReport(reports.length > 0)
      })
      .catch(() => {
        if (!cancelled) setHasReport(false)
      })
    return () => {
      cancelled = true
    }
  }, [isChecking, hasReport, setHasReport])

  if (isChecking) {
    return <BrandLoader />
  }

  return (
    <div
      className={cn(
        // isolate keeps -z-10 orbs inside this shell (avoids black peek-through
        // in scrollbar gutters). overflow-x-hidden kills the horizontal bar.
        "relative isolate flex flex-col overflow-x-hidden bg-[#f1f4f6]",
        // Full-bleed: one viewport shell; only main scrolls when content overflows.
        isFullBleed ? "h-svh overflow-y-hidden" : "min-h-svh"
      )}
    >
      <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden" aria-hidden>
        <div className="absolute top-[-20%] left-[-10%] h-[28rem] w-[28rem] rounded-full bg-primary/[0.07] blur-3xl" />
        <div className="absolute right-[-8%] bottom-[-15%] h-[24rem] w-[24rem] rounded-full bg-primary/[0.05] blur-3xl" />
      </div>

      <motion.header
        initial={{ opacity: 0, y: -6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: "easeOut" }}
        className="z-40 shrink-0 border-b border-primary/10 bg-primary/[0.07] backdrop-blur-xl"
      >
        <div className="flex h-14 items-center justify-between px-5 sm:px-8">
          <Logo href="/dashboard" size="md" />
          <div className="flex items-center gap-2">
            {pathname !== "/dashboard" && hasReport ? (
              <Button
                variant="ghost"
                className="h-9 rounded-full px-3.5"
                render={<Link href="/dashboard" />}
                nativeButton={false}
              >
                <LayoutDashboard className="size-4" />
                Dashboard
              </Button>
            ) : null}
            <UserMenu />
          </div>
        </div>
      </motion.header>

      <motion.main
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className={cn(
          "relative flex min-h-0 flex-1 flex-col",
          isFullBleed && !usesInnerScroll && "overflow-x-hidden overflow-y-auto",
          isFullBleed && usesInnerScroll && "overflow-hidden",
          !isFullBleed && "mx-auto w-full max-w-6xl px-6 py-10 sm:py-12"
        )}
      >
        {children}
      </motion.main>
    </div>
  )
}
