import { authenticatedRequest } from "@/lib/auth/authSession"
import type { MessageResponse } from "@/lib/auth/authApi"

export function submitSupportRequest(subject: string, message: string, reportId?: string): Promise<MessageResponse> {
  return authenticatedRequest<MessageResponse>("/support/requests", {
    body: { subject, message, report_id: reportId ?? null },
  })
}
