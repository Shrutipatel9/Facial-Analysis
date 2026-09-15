import { useEffect, useState } from "react"

import * as photoApi from "@/lib/photos/photoApi"

/**
 * Object URL for the user's front-angle photo -- the CV pass's landmark
 * overlays (Prototypicality/Proportions/Symmetry/Face Shape) are all
 * normalized against this exact photo, so it's the only correct image to
 * draw them over. Fetched once and shared by every assessment page that
 * needs it (see FacialAssessmentsSection), not refetched per page.
 */
export function useFrontPhotoUrl(): string | null {
  const [url, setUrl] = useState<string | null>(null)

  useEffect(() => {
    let objectUrl: string | null = null
    let cancelled = false

    async function load() {
      try {
        const status = await photoApi.getStatus()
        const front = status.angles.find((entry) => entry.angle === "front")?.photo
        if (!front || cancelled) return
        const blob = await photoApi.getPhotoFile(front.id)
        if (cancelled) return
        objectUrl = URL.createObjectURL(blob)
        setUrl(objectUrl)
      } catch {
        // No overlay image is a degraded-but-safe state -- the assessment
        // score/label content still renders without it.
      }
    }
    void load()

    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [])

  return url
}
