"use client"

import { Loader2, Receipt } from "lucide-react"
import { useEffect, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { getErrorMessage } from "@/lib/api/getErrorMessage"
import { formatCurrencyCents, formatDate } from "@/lib/format"
import * as paymentApi from "@/lib/payments/paymentApi"
import type { PaymentSummary } from "@/lib/payments/paymentApi"

const STATUS_VARIANT = {
  succeeded: "default",
  pending: "secondary",
  failed: "destructive",
} as const

export function PaymentHistoryCard() {
  const [payments, setPayments] = useState<PaymentSummary[] | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    paymentApi
      .listPayments()
      .then((list) => {
        if (!cancelled) setPayments(list)
      })
      .catch((err) => {
        if (!cancelled) setErrorMessage(getErrorMessage(err))
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-border bg-card p-6">
      <div className="flex items-center gap-2.5">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
          <Receipt className="size-4" />
        </span>
        <h2 className="font-heading text-lg font-semibold tracking-tight">Payment history</h2>
      </div>

      {errorMessage ? (
        <p className="text-sm text-destructive">{errorMessage}</p>
      ) : payments === null ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="size-5 animate-spin text-primary/50" aria-label="Loading" />
        </div>
      ) : payments.length === 0 ? (
        <p className="text-sm text-muted-foreground">No payments yet.</p>
      ) : (
        <ul className="divide-y divide-border">
          {payments.map((payment) => (
            <li key={payment.id} className="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0">
              <div className="space-y-0.5">
                <p className="text-sm font-medium">{formatCurrencyCents(payment.amount_cents, payment.currency)}</p>
                <p className="text-xs text-muted-foreground">{formatDate(payment.created_at)}</p>
              </div>
              <Badge variant={STATUS_VARIANT[payment.status]}>{payment.status}</Badge>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
