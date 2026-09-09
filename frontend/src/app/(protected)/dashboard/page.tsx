"use client"

import { motion } from "motion/react"

import { PaymentHistoryCard } from "@/components/dashboard/PaymentHistoryCard"
import { ProfileCard } from "@/components/dashboard/ProfileCard"
import { ReportSummaryCard } from "@/components/dashboard/ReportSummaryCard"
import { useAuthStore } from "@/store/authStore"

/** Prefers the account's full_name (captured at signup); falls back to an
 * email-derived guess only for accounts created before that field existed. */
function displayName(user: { full_name: string | null; email: string } | null | undefined): string {
  const firstName = user?.full_name?.trim().split(/\s+/)[0]
  if (firstName) return firstName

  const email = user?.email
  if (!email) return "there"
  const local = email.split("@")[0] ?? email
  const cleaned = local.replace(/[._-]+/g, " ").trim()
  if (!cleaned) return "there"
  return cleaned.replace(/\b\w/g, (c) => c.toUpperCase())
}

/**
 * Post-onboarding workspace (FR-017) -- incomplete users are routed to
 * /questionnaire (useQuestionnaireGuard) then /photos
 * (usePhotoUploadGuard) then /payment (usePaymentGuard) then /analysis
 * (useAnalysisGuard), so this page is only ever reached once all four are
 * complete. Composes three independently-loading sections (report,
 * payment history, profile) rather than one combined fetch -- each hits
 * its own already-existing endpoint (GET /reports, GET /payments, GET
 * /users/me), so one slow/failed section never blocks the others.
 */
export default function DashboardPage() {
  const user = useAuthStore((state) => state.user)

  return (
    <div className="w-full">
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className="mb-8 space-y-1"
      >
        <h1 className="font-heading text-2xl font-semibold tracking-tight sm:text-3xl">
          Welcome back, {displayName(user)}
        </h1>
        <p className="text-sm text-muted-foreground">Your reports, payments, and account, all in one place.</p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: "easeOut", delay: 0.05 }}
        className="grid grid-cols-1 gap-5 lg:grid-cols-[1.4fr_1fr]"
      >
        <div className="flex flex-col gap-5">
          <ReportSummaryCard />
          <PaymentHistoryCard />
        </div>
        <ProfileCard />
      </motion.div>
    </div>
  )
}
