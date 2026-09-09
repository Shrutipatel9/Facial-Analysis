import { authenticatedBlobRequest, authenticatedFormRequest, authenticatedRequest } from "@/lib/api/apiClient"

export type CaptureMethod = "upload" | "camera"
export type ValidationStatus = "passed" | "failed"

export interface CheckResult {
  check: string
  passed: boolean
  reason: string | null
}

export interface PhotoOut {
  id: string
  angle: string
  capture_method: CaptureMethod
  validation_status: ValidationStatus
  checks: CheckResult[]
  uploaded_at: string
}

export interface PhotoAngleStatus {
  angle: string
  label: string
  instruction: string
  photo: PhotoOut | null
}

export interface PhotoSetStatusResponse {
  angles: PhotoAngleStatus[]
  completed: boolean
}

export function getStatus(): Promise<PhotoSetStatusResponse> {
  return authenticatedRequest<PhotoSetStatusResponse>("/photos/status", { method: "GET" })
}

export function getPhoto(id: string): Promise<PhotoOut> {
  return authenticatedRequest<PhotoOut>(`/photos/${id}`, { method: "GET" })
}

/** The actual stored image bytes -- used to show a persistent preview of
 * an already-uploaded angle after a reload (see PhotoCaptureStep.tsx). */
export function getPhotoFile(id: string): Promise<Blob> {
  return authenticatedBlobRequest(`/photos/${id}/file`)
}

export function uploadPhoto(angle: string, captureMethod: CaptureMethod, blob: Blob): Promise<PhotoOut> {
  const formData = new FormData()
  formData.append("angle", angle)
  formData.append("capture_method", captureMethod)
  formData.append("file", blob, `${angle}.jpg`)
  return authenticatedFormRequest<PhotoOut>("/photos", formData)
}
