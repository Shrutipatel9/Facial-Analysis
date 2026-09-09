"use client"

import { AlertCircle, ArrowRight, CheckCircle2, Loader2, Sparkles } from "lucide-react"
import { motion } from "motion/react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { useEffect, useRef, useState } from "react"
import { toast } from "sonner"

import { FacialScanVisual } from "@/components/auth/FacialScanVisual"
import { Button } from "@/components/ui/button"
import { getErrorMessage } from "@/lib/api/getErrorMessage"
import * as analysisApi from "@/lib/analysis/analysisApi"
import { useAnalysisStore } from "@/store/analysisStore"
import { usePaymentStore } from "@/store/paymentStore"

const POLL_INTERVAL_MS = 3000

/**
 * Payment-before-analysis (FR-015, BR-001): reachable only once payment has
 * already succeeded (usePaymentGuard routes here; the defensive redirect
 * below covers a direct URL jump before then). The actual analysis trigger
 * stays a manual "Start Analysis" click, same as before payment gating
 * existed -- the payment webhook only flips Payment.status, it does not
 * auto-run the pipeline (see Backend/app/services/payment_service.py's
 * module docstring for why: auto-triggering made the whole "analyzing"
 * step invisible when the pipeline finished in a couple of seconds).
 *
 * Four states -- ready/processing/failed/completed. On completion this
 * screen shows an "Analysis complete" state with a manual "View report"
 * button to /report -- no auto-redirect anywhere (an earlier version
 * auto-redirected to /dashboard the instant status flipped; the user
 * explicitly asked for the original flow back: analysis done -> View
 * report -> /report, full stop, never automatically to /dashboard).
 */
export function AnalysisScreen() {
  const router = useRouter()
  const status = useAnalysisStore((state) => state.status)
  const analysisId = useAnalysisStore((state) => state.analysisId)
  const setStatus = useAnalysisStore((state) => state.setStatus)
  const paymentStatus = usePaymentStore((state) => state.status)
  const [isStarting, setIsStarting] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const errorFetchedFor = useRef<string | null>(null)

  // Defensive fallback for direct URL navigation before payment succeeded
  // -- usePaymentGuard only bounces a user AWAY from /payment once already
  // paid, it doesn't stop a forward jump straight to /analysis. The
  // backend's own guard (PaymentRequiredError) is the real enforcement
  // point; this just avoids showing a "Start Analysis" button that would
  // immediately 402 if clicked.
  useEffect(() => {
    if (paymentStatus !== null && paymentStatus !== "succeeded") {
      router.replace("/payment")
    }
  }, [paymentStatus, router])

  useEffect(() => {
    if (status !== "processing") return
    const interval = setInterval(() => {
      analysisApi
        .getStatus()
        .then((result) => setStatus(result.status, result.analysis_id))
        .catch(() => {
          // Transient network errors: keep polling silently rather than
          // showing an error for what is likely just a blip.
        })
    }, POLL_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [status, setStatus])

  useEffect(() => {
    if (status !== "failed" || !analysisId || errorFetchedFor.current === analysisId) return
    errorFetchedFor.current = analysisId
    analysisApi
      .getAnalysis(analysisId)
      .then((full) => setErrorMessage(full.error_message))
      .catch(() => setErrorMessage(null))
  }, [status, analysisId])

  async function handleStart() {
    setIsStarting(true)
    setErrorMessage(null)
    try {
      const result = await analysisApi.triggerAnalysis()
      setStatus(result.status, result.id)
      toast.success("Analysis started.")
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setIsStarting(false)
    }
  }

  let content: React.ReactNode

  if (status === "processing") {
    content = (
      <div className="mx-auto w-full max-w-xl space-y-6 text-center">
        <Loader2 className="mx-auto size-10 animate-spin text-primary" aria-hidden />
        <h1 className="font-sans text-3xl font-semibold tracking-tight sm:text-4xl">
          Analyzing your photos…
        </h1>
        <p className="text-base leading-relaxed text-muted-foreground">
          This usually takes approximately 1–2 minutes. Feel free to leave this page, we&apos;ll pick up
          where you left off when you come back.
        </p>
      </div>
    )
  } else if (status === "failed") {
    content = (
      <div className="mx-auto w-full max-w-xl space-y-6 text-center">
        <span className="mx-auto flex size-14 items-center justify-center rounded-full bg-destructive/10 text-destructive">
          <AlertCircle className="size-6" />
        </span>
        <h1 className="font-sans text-3xl font-semibold tracking-tight sm:text-4xl">Analysis failed</h1>
        <p className="text-base leading-relaxed text-muted-foreground">
          {errorMessage ?? "Something went wrong while analyzing your photos."}
        </p>
        <Button type="button" className="h-11 rounded-full px-8" onClick={handleStart} disabled={isStarting}>
          {isStarting ? <Loader2 className="size-4 animate-spin" /> : null}
          Try again
        </Button>
      </div>
    )
  } else if (status === "completed") {
    content = (
      <div className="mx-auto w-full max-w-xl space-y-6 text-center">
        <span className="mx-auto flex size-14 items-center justify-center rounded-full bg-success/15 text-success">
          <CheckCircle2 className="size-6" />
        </span>
        <h1 className="font-sans text-3xl font-semibold tracking-tight sm:text-4xl">Analysis complete</h1>
        <p className="text-base leading-relaxed text-muted-foreground">
          Your facial analysis is ready. View your full report now.
        </p>
        <Button
          type="button"
          className="h-11 rounded-full px-8"
          render={<Link href="/report" />}
          nativeButton={false}
        >
          View report
          <ArrowRight />
        </Button>
      </div>
    )
  } else {
    content = (
      <div className="mx-auto w-full max-w-xl space-y-6 text-center">
        <span className="mx-auto flex size-14 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-md shadow-primary/20">
          <Sparkles className="size-6" />
        </span>
        <div className="space-y-1">
          <h1 className="font-sans text-4xl font-semibold tracking-tight sm:text-5xl">Payment confirmed</h1>
        </div>
        <p className="text-base leading-relaxed text-muted-foreground">
          We&apos;ll combine your photos and questionnaire answers to generate your facial analysis.
          This takes approximately 1–2 minutes.
        </p>
        <Button type="button" className="h-11 rounded-full px-8" onClick={handleStart} disabled={isStarting}>
          {isStarting ? <Loader2 className="size-4 animate-spin" /> : null}
          Start analysis
          <ArrowRight />
        </Button>
      </div>
    )
  }

  return (
    <section className="grid min-h-full flex-1 lg:grid-cols-[0.8fr_1.2fr]">
      <aside className="relative hidden flex-col items-center justify-center gap-8 px-8 py-10 lg:flex">
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

      <div className="flex flex-col items-center justify-center px-5 py-8 sm:px-8 lg:pr-14 lg:pl-6">
        {content}
      </div>
    </section>
  )
}
