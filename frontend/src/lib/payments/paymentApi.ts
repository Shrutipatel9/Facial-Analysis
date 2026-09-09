import { authenticatedRequest } from "@/lib/api/apiClient"

export type PaymentStatus = "unpaid" | "pending" | "succeeded"

export interface PaymentStatusResponse {
  status: PaymentStatus
  price_cents: number
  price_currency: string
}

export interface CheckoutResponse {
  checkout_url: string
}

export interface PaymentSummary {
  id: string
  status: "pending" | "succeeded" | "failed"
  amount_cents: number
  currency: string
  created_at: string
}

/** No report/analysis exists yet at checkout time -- payment gates the
 * START of analysis itself (see Backend/app/services/analysis_service.py's
 * trigger_analysis), so this call takes no body. */
export function createCheckoutSession(): Promise<CheckoutResponse> {
  return authenticatedRequest<CheckoutResponse>("/payments/checkout", { method: "POST" })
}

export function getStatus(): Promise<PaymentStatusResponse> {
  return authenticatedRequest<PaymentStatusResponse>("/payments/status", { method: "GET" })
}

export function listPayments(): Promise<PaymentSummary[]> {
  return authenticatedRequest<PaymentSummary[]>("/payments", { method: "GET" })
}
