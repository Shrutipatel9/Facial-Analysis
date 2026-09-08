"use client"

import { usePathname, useRouter } from "next/navigation"
import { useEffect, useRef } from "react"

import * as photoApi from "@/lib/photos/photoApi"
import { usePhotoStore } from "@/store/photoStore"

const PHOTOS_PATH = "/photos"
const DASHBOARD_PATH = "/dashboard"

/**
 * Loads photo-set status and routes, mirroring useQuestionnaireGuard's
 * force-routing shape exactly (BR-004's "auto-route until completed"
 * pattern -- see docs/photo_capture_spec.md):
 * - incomplete on /dashboard → /photos
 * - complete on /photos → /dashboard
 *
 * Only enabled once the questionnaire guard has already cleared (a user
 * can't sensibly reach /photos before finishing the questionnaire) -- see
 * (protected)/layout.tsx's wiring.
 */
export function usePhotoUploadGuard(enabled: boolean): { isChecking: boolean } {
  const completed = usePhotoStore((state) => state.completed)
  const setStatus = usePhotoStore((state) => state.setStatus)
  const pathname = usePathname()
  const router = useRouter()
  const hasFetched = useRef(false)

  useEffect(() => {
    if (!enabled || hasFetched.current) return
    hasFetched.current = true
    photoApi
      .getStatus()
      .then((status) => setStatus(status))
      .catch(() => {
        hasFetched.current = false
      })
  }, [enabled, setStatus])

  useEffect(() => {
    if (completed === null) return
    if (!completed && pathname === DASHBOARD_PATH) {
      router.replace(PHOTOS_PATH)
      return
    }
    if (completed && pathname === PHOTOS_PATH) {
      router.replace(DASHBOARD_PATH)
    }
  }, [completed, pathname, router])

  return { isChecking: enabled && completed === null }
}
