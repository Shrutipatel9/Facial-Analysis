"use client"

import { meridian } from "@/lib/report/meridianTokens"
import type { FacialAssessment } from "@/lib/reports/reportApi"

/**
 * Proportions' overlay -- 3 plain CSS-positioned horizontal lines over the
 * front photo (hairline/brow/nose-base/chin boundary y-values, all
 * normalized 0-1 top-down), per report_design_spec.md's "no SVG needed"
 * note for this one.
 */
export function FacialThirdsOverlay({ photoUrl, overlay }: { photoUrl: string | null; overlay: FacialAssessment["overlay"] }) {
  const hairlineY = overlay?.hairline_y as number | undefined
  const browY = overlay?.brow_y as number | undefined
  const noseBaseY = overlay?.nose_base_y as number | undefined
  const chinY = overlay?.chin_y as number | undefined

  if (!photoUrl || hairlineY == null || browY == null || noseBaseY == null || chinY == null) {
    return null
  }

  return (
    <div className="relative overflow-hidden rounded-lg">
      {/* eslint-disable-next-line @next/next/no-img-element -- authenticated blob URL */}
      <img src={photoUrl} alt="Your uploaded photo with facial-thirds boundaries marked" className="block w-full" />
      <ThirdLine y={hairlineY} label="Hairline (approx.)" />
      <ThirdLine y={browY} label="Brow" />
      <ThirdLine y={noseBaseY} label="Nose base" />
      <ThirdLine y={chinY} label="Chin" />
    </div>
  )
}

function ThirdLine({ y, label }: { y: number; label: string }) {
  return (
    <div className="absolute inset-x-0" style={{ top: `${y * 100}%` }}>
      <div className="h-px w-full" style={{ backgroundColor: meridian.accent.secondary }} />
      <span
        className="absolute left-1 -translate-y-1/2 rounded px-1 text-[10px] font-medium"
        style={{ backgroundColor: meridian.surface.card, color: meridian.accent.secondary }}
      >
        {label}
      </span>
    </div>
  )
}
