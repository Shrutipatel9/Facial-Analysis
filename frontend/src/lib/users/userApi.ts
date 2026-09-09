import { authenticatedRequest } from "@/lib/api/apiClient"

export interface UserProfile {
  id: string
  email: string
  full_name: string | null
  role: string
  verification_status: "pending" | "verified"
  created_at: string
}

export function getMe(): Promise<UserProfile> {
  return authenticatedRequest<UserProfile>("/users/me", { method: "GET" })
}
