import { authenticatedBlobRequest, authenticatedRequest } from "@/lib/api/apiClient"

export type AiVisualKind = "hairstyle" | "outfit" | "aging" | "potential"

export interface AiVisual {
  id: string
  kind: AiVisualKind
  variation_index: number
  // "pending" | "generating" | "generated" | "failed"
  status: string
  name: string | null
  is_recommended: boolean
  attributes: Record<string, string | number> | null
  explanation: string | null
  error_reason: string | null
}

/** Lazy get-or-create + trigger-once (BR-006) -- idempotent, safe to call
 * repeatedly once variations already exist for this kind. */
export function createVisuals(kind: AiVisualKind): Promise<AiVisual[]> {
  return authenticatedRequest<AiVisual[]>(`/ai-visuals/${kind}`, { method: "POST" })
}

/** Read-only -- returns [] before createVisuals has ever been called for this kind. */
export function getVisuals(kind: AiVisualKind): Promise<AiVisual[]> {
  return authenticatedRequest<AiVisual[]>(`/ai-visuals/${kind}`, { method: "GET" })
}

/** Only call once a variation's status is "generated", otherwise this 404s. */
export function getVisualImage(kind: AiVisualKind, variationId: string): Promise<Blob> {
  return authenticatedBlobRequest(`/ai-visuals/${kind}/${variationId}/image`)
}
