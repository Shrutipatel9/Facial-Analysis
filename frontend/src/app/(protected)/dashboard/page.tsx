"use client"

import { CheckCircle2, Sparkles } from "lucide-react"
import { motion } from "motion/react"

import { FacialScanVisual } from "@/components/auth/FacialScanVisual"
import { useAuthStore } from "@/store/authStore"

function displayName(email: string | undefined): string {
  if (!email) return "there"
  const local = email.split("@")[0] ?? email
  const cleaned = local.replace(/[._-]+/g, " ").trim()
  if (!cleaned) return "there"
  return cleaned.replace(/\b\w/g, (c) => c.toUpperCase())
}

/**
 * Post-onboarding workspace. Incomplete users are routed to /questionnaire
 * (useQuestionnaireGuard) then /photos (usePhotoUploadGuard) — this page
 * is only ever reached once both are complete.
 */
export default function DashboardPage() {
  const user = useAuthStore((state) => state.user)

  return (
    <section className="grid min-h-full flex-1 lg:grid-cols-[0.95fr_1.05fr]">
      <div className="relative flex min-h-[40vh] flex-col items-center justify-center gap-6 px-6 py-10 lg:min-h-0 lg:px-10">
        <motion.div
          className="absolute inset-[12%] rounded-full bg-primary/[0.06] blur-3xl"
          animate={{ scale: [1, 1.06, 1], opacity: [0.5, 0.85, 0.5] }}
          transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.55, ease: "easeOut" }}
          className="relative"
        >
          <FacialScanVisual className="h-[min(48vh,340px)] w-auto" tone="onLight" />
        </motion.div>
        <p className="relative text-center text-xs font-medium tracking-[0.22em] text-primary/55 uppercase">
          Facial analysis ready
        </p>
      </div>

      <div className="flex items-center px-5 pb-10 sm:px-8 lg:px-10 lg:py-10">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="w-full max-w-md space-y-6 rounded-2xl border border-border bg-card p-8 sm:p-10"
        >
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/12 bg-primary/[0.06] px-3 py-1 text-xs font-medium text-primary">
            <Sparkles className="size-3.5" />
            Your workspace
          </div>

          <div className="space-y-3">
            <h1 className="font-heading text-3xl font-semibold tracking-tight text-balance sm:text-[2.35rem] sm:leading-tight">
              Welcome back, {displayName(user?.email)}
            </h1>
            <p className="text-[15px] leading-relaxed text-muted-foreground text-pretty">
              Your questionnaire answers and photos are ready to contextualize the AI narrative once
              analysis goes live.
            </p>
          </div>

          <div className="flex items-start gap-3 rounded-xl border border-border bg-muted/30 p-4">
            <span className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
              <CheckCircle2 className="size-4" />
            </span>
            <div>
              <p className="text-sm font-medium">Onboarding complete</p>
              <p className="mt-0.5 text-sm text-muted-foreground">
                You&apos;re ready for the next modules when they ship.
              </p>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
