import { create } from "zustand"

import type { PaymentStatus } from "@/lib/payments/paymentApi"

/**
 * Payment-before-analysis gate status (FR-015, FR-016, BR-001). Its own
 * store, same module-boundary convention as questionnaireStore/photoStore/
 * analysisStore -- sits between photos and analysis in the onboarding
 * chain (see lib/onboarding/nextStep.ts).
 *
 * Deliberately NOT persisted, same reasoning as photoStore/analysisStore:
 * status is trivially re-fetchable from GET /payments/status on mount.
 */
interface PaymentState {
  /** From GET /payments/status -- null until fetched once. */
  status: PaymentStatus | null
  priceCents: number | null
  priceCurrency: string | null

  setStatus: (status: PaymentStatus, priceCents: number, priceCurrency: string) => void
  reset: () => void
}

export const usePaymentStore = create<PaymentState>()((set) => ({
  status: null,
  priceCents: null,
  priceCurrency: null,

  setStatus: (status, priceCents, priceCurrency) => set({ status, priceCents, priceCurrency }),

  reset: () => set({ status: null, priceCents: null, priceCurrency: null }),
}))
