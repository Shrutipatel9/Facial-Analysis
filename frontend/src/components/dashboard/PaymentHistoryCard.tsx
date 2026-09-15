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

export function PaymentHistoryCard({ embedded = false }: { embedded?: boolean }) {
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

  const body = (
    <>
      {!embedded ? (
        <div className="flex items-center gap-2.5">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Receipt className="size-4" />
          </span>
          <h2 className="font-heading text-lg font-semibold tracking-tight">Payment history</h2>
        </div>
      ) : null}

      {errorMessage ? (
        <p className="text-sm text-destructive">{errorMessage}</p>
      ) : payments === null ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="size-5 animate-spin text-primary/50" aria-label="Loading" />
        </div>
      ) : payments.length === 0 ? (
        <p className="text-sm text-muted-foreground">No payments yet.</p>
      ) : (
        <ul className={embedded ? "divide-y divide-border/70" : "divide-y divide-border"}>
          {payments.map((payment) => (
            <li
              key={payment.id}
              className="flex items-center justify-between gap-3 py-3.5 first:pt-0 last:pb-0"
            >
              <div className="flex min-w-0 items-center gap-3">
                {embedded ? (
                  <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground">
                    <Receipt className="size-3.5" />
                  </span>
                ) : null}
                <div className="min-w-0 space-y-0.5">
                  <p className="text-sm font-medium text-foreground">
                    {formatCurrencyCents(payment.amount_cents, payment.currency)}
                  </p>
                  <p className="text-xs text-muted-foreground">{formatDate(payment.created_at)}</p>
                </div>
              </div>
              <Badge variant={STATUS_VARIANT[payment.status]}>{payment.status}</Badge>
            </li>
          ))}
        </ul>
      )}
    </>
  )

  if (embedded) {
    return (
      <div className="rounded-2xl border border-border/80 bg-white p-5 shadow-[0_1px_2px_rgba(0,0,0,0.04)] sm:p-6">
        {body}
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-border/80 bg-card p-6 shadow-[0_10px_30px_-18px_rgba(20,55,75,0.28)]">
      {body}
    </div>
  )
}
