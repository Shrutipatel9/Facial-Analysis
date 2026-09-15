"use client"

import { CreditCard, Loader2, Wallet } from "lucide-react"
import { useEffect, useState } from "react"
import { toast } from "sonner"

import { SettingsCard, SettingsSectionHeader } from "./settingsChrome"
import { PaymentHistoryCard } from "@/components/dashboard/PaymentHistoryCard"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { getErrorMessage } from "@/lib/api/getErrorMessage"
import { formatCurrencyCents } from "@/lib/format"
import * as paymentApi from "@/lib/payments/paymentApi"
import type { PaymentStatusResponse } from "@/lib/payments/paymentApi"

/**
 * Every user who can reach /settings has already paid (payment gates
 * analysis start, and this app has exactly 0-or-1 reports per user -- no
 * repurchase flow exists). "Pay with Stripe" is therefore NOT wired to
 * POST /payments/checkout (that would deterministically 409 ALREADY_PAID,
 * whose copy was written for the pre-analysis payment gate, not here) --
 * clicking it just confirms, locally, that nothing further is owed.
 * "Pay with PayPal" stays genuinely disabled, matching the reference's
 * "visible but disabled, missing keys" status pill (OI-3/BR-012).
 */
export function BillingSection() {
  const [status, setStatus] = useState<PaymentStatusResponse | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    paymentApi
      .getStatus()
      .then((result) => {
        if (!cancelled) setStatus(result)
      })
      .catch((err) => {
        if (!cancelled) setErrorMessage(getErrorMessage(err))
      })
    return () => {
      cancelled = true
    }
  }, [])

  const price = status ? formatCurrencyCents(status.price_cents, status.price_currency) : null

  return (
    <div className="w-full space-y-5">
      <SettingsSectionHeader title="Billing" description="Your current product and payment history." />

      <SettingsCard className="space-y-5">
        <div className="space-y-1">
          <h3 className="text-base font-semibold tracking-tight text-foreground">Facial Analysis Report</h3>
          <p className="text-sm leading-relaxed text-muted-foreground">
            One-time full facial analysis, all 11 features, AI visuals, and PDF export.
          </p>
        </div>

        {errorMessage ? (
          <p className="text-sm text-destructive">{errorMessage}</p>
        ) : status === null ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="size-5 animate-spin text-primary/50" aria-label="Loading" />
          </div>
        ) : (
          <div className="space-y-4 border-t border-border/70 pt-5">
            <p className="font-heading text-3xl font-semibold tracking-tight text-foreground">{price}</p>
            <div className="flex flex-wrap items-center gap-2.5">
              <Button
                type="button"
                className="h-10 rounded-full px-5"
                onClick={() =>
                  toast.info("You already own this report -- no further payment is needed.")
                }
              >
                <CreditCard className="size-4" />
                Pay with Stripe
              </Button>
              <Button type="button" variant="outline" className="h-10 rounded-full px-5" disabled>
                <Wallet className="size-4" />
                Pay with PayPal
              </Button>
              <Badge variant="secondary">PayPal: missing keys</Badge>
            </div>
          </div>
        )}
      </SettingsCard>

      <div className="space-y-3">
        <h3 className="text-[11px] font-semibold tracking-[0.12em] text-muted-foreground uppercase">
          Recent Payments
        </h3>
        <PaymentHistoryCard embedded />
      </div>
    </div>
  )
}
