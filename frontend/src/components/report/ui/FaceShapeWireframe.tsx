"use client"

import { meridian } from "@/lib/report/meridianTokens"
import type { FacialAssessment } from "@/lib/reports/reportApi"

/**
 * SVG face-outline polygon over the front photo -- shared by Prototypicality
 * (its "Shape Analysis" wireframe) and Face Shape (its diagram), matching
 * the backend's shared `_face_outline_points` helper (both assessments
 * emit the same `overlay.face_outline` shape).
 */
export function FaceShapeWireframe({ photoUrl, overlay }: { photoUrl: string | null; overlay: FacialAssessment["overlay"] }) {
  const outline = overlay?.face_outline as [number, number][] | undefined

  if (!photoUrl || !outline || outline.length === 0) {
    return null
  }

  const points = outline.map(([x, y]) => `${x * 100},${y * 100}`).join(" ")

  return (
    <div className="relative overflow-hidden rounded-lg">
      {/* eslint-disable-next-line @next/next/no-img-element -- authenticated blob URL */}
      <img src={photoUrl} alt="Your uploaded photo with the face outline traced" className="block w-full" />
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="absolute inset-0 size-full" aria-hidden>
        <polygon points={points} fill="none" stroke={meridian.accent.secondary} strokeWidth={0.4} />
      </svg>
    </div>
  )
}
