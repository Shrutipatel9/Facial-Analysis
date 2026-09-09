"use client"

import { Download, Loader2, Lock, ScanFace, Sparkles } from "lucide-react"
import { motion } from "motion/react"
import { useRouter, useSearchParams } from "next/navigation"
import { useEffect, useRef, useState } from "react"
import { toast } from "sonner"

import { FacialScanVisual } from "@/components/auth/FacialScanVisual"
import { Button } from "@/components/ui/button"
import { ConfirmDialog } from "@/components/ui/confirm-dialog"
import { getErrorMessage } from "@/lib/api/getErrorMessage"
import { formatCurrencyCents } from "@/lib/format"
import * as paymentApi from "@/lib/payments/paymentApi"
import { usePaymentStore } from "@/store/paymentStore"

const POLL_INTERVAL_MS = 3000

/**
 * Meridian-inspired card styling, same tokens as the report cards
 * (docs/report_design_spec.md) -- applied narrowly to this one card, not a
 * full-page wash.
 */
const MERIDIAN = {
  card: "#FFFFFF",
  ink: "#2B2822",
  inkMuted: "#6B6558",
  accent: "#A8461F",
  accentSecondary: "#3E6E64",
  recessed: "#EFEAE0",
}

const INCLUDES = [
  { icon: ScanFace, text: "In-depth breakdowns for all 11 features -- hair, eyes, jaw, skin and more" },
  { icon: Sparkles, text: "Strengths, areas of note, and personalized improvement ideas per feature" },
  { icon: Download, text: "A downloadable, print-ready PDF of your complete report" },
] as const

/**
 * Payment-before-analysis (FR-015, FR-016, BR-001): reached once
 * questionnaire + photos are both complete -- analysis cannot even be
 * triggered until payment succeeds (Backend/app/services/analysis_service.
 * py's trigger_analysis), so this page is a hard gate, not an optional
 * upsell shown alongside a free teaser. usePaymentGuard (mounted in
 * (protected)/layout.tsx) owns the actual redirect away once status flips
 * to "succeeded" -- this component only needs to keep the shared
 * paymentStore up to date via polling, same interval-poll shape as
 * AnalysisScreen.tsx.
 */
export function PaymentScreen() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const status = usePaymentStore((state) => state.status)
  const priceCents = usePaymentStore((state) => state.priceCents)
  const priceCurrency = usePaymentStore((state) => state.priceCurrency)
  const setStatus = usePaymentStore((state) => state.setStatus)
  const [isRedirecting, setIsRedirecting] = useState(false)
  const hasHandledQueryParam = useRef(false)

  // Returning from Stripe's hosted checkout -- strip the query param so a
  // reload doesn't re-show the toast, and surface a cancellation
  // explicitly. A success needs no toast: the poll below picks up
  // "succeeded" within one tick and usePaymentGuard redirects onward.
  useEffect(() => {
    if (hasHandledQueryParam.current) return
    const payment = searchParams.get("payment")
    if (!payment) return
    hasHandledQueryParam.current = true
    if (payment === "cancelled") {
      toast.info("Payment cancelled. You can try again any time.")
    }
    router.replace("/payment")
  }, [searchParams, router])

  useEffect(() => {
    if (status === "succeeded") return
    const interval = setInterval(() => {
      paymentApi
        .getStatus()
        .then((result) => setStatus(result.status, result.price_cents, result.price_currency))
        .catch(() => {
          // Transient network errors: keep polling silently rather than
          // showing an error for what is likely just a blip.
        })
    }, POLL_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [status, setStatus])

  async function handleUnlock() {
    setIsRedirecting(true)
    try {
      const { checkout_url } = await paymentApi.createCheckoutSession()
      window.location.href = checkout_url
    } catch (err) {
      toast.error(getErrorMessage(err))
      setIsRedirecting(false)
    }
  }

  let content: React.ReactNode

  if (status === "succeeded" || status === null) {
    content = (
      <div className="mx-auto w-full max-w-xl text-center">
        <Loader2 className="mx-auto size-8 animate-spin text-primary/50" aria-label="Loading" />
      </div>
    )
  } else {
    const price = priceCents !== null && priceCurrency !== null ? formatCurrencyCents(priceCents, priceCurrency) : null
    content = (
      <div className="mx-auto flex w-full max-w-lg flex-1 flex-col items-center justify-center px-2 text-center">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: "easeOut" }}
          className="w-full space-y-6 rounded-2xl p-7 shadow-sm"
          style={{ backgroundColor: MERIDIAN.card }}
        >
          <span
            className="mx-auto flex size-14 items-center justify-center rounded-full"
            style={{ backgroundColor: MERIDIAN.recessed, color: MERIDIAN.accent }}
          >
            <Lock className="size-6" aria-hidden />
          </span>

          <div className="space-y-2">
            <h1 className="text-2xl font-semibold tracking-tight" style={{ color: MERIDIAN.ink }}>
              Unlock your facial analysis
            </h1>
            <p className="text-sm leading-relaxed" style={{ color: MERIDIAN.inkMuted }}>
              Your photos and questionnaire are ready. Complete a one-time payment to start your
              analysis and generate your full report.
            </p>
          </div>

          <ul className="space-y-3 text-left">
            {INCLUDES.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-start gap-3">
                <span
                  className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full"
                  style={{ backgroundColor: MERIDIAN.recessed, color: MERIDIAN.accentSecondary }}
                >
                  <Icon className="size-3.5" aria-hidden />
                </span>
                <span className="text-sm leading-relaxed" style={{ color: MERIDIAN.inkMuted }}>
                  {text}
                </span>
              </li>
            ))}
          </ul>

          <ConfirmDialog
            variant="default"
            title="Start your analysis"
            description={
              price
                ? `You'll be redirected to Stripe's secure checkout to complete a one-time payment of ${price}. Your analysis starts automatically the moment payment is confirmed.`
                : "You'll be redirected to Stripe's secure checkout to complete a one-time payment."
            }
            confirmLabel={price ? `Pay ${price}` : "Continue"}
            onConfirm={handleUnlock}
            trigger={
              <Button type="button" className="h-11 w-full rounded-full px-8" disabled={isRedirecting}>
                {isRedirecting ? <Loader2 className="size-4 animate-spin" /> : null}
                {price ? `Unlock & Start Analysis -- ${price}` : "Unlock & Start Analysis"}
              </Button>
            }
          />
        </motion.div>
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
