"use client"

import { ReportPhotoFrame } from "./ReportPhotoFrame"
import { meridian } from "@/lib/report/meridianTokens"
import type { FacialAssessment } from "@/lib/reports/reportApi"

interface SymmetryPair {
  feature: string
  left: [number, number]
  right: [number, number]
}

/**
 * Symmetry's overlay -- the vertical midline axis plus each mirrored-pair
 * marker, drawn as an SVG layer over the front photo.
 */
export function SymmetryAxisOverlay({ photoUrl, overlay }: { photoUrl: string | null; overlay: FacialAssessment["overlay"] }) {
  const axisX = overlay?.axis_x as number | undefined
  const pairs = overlay?.pairs as SymmetryPair[] | undefined

  if (!photoUrl || axisX == null || !pairs || pairs.length === 0) {
    return null
  }

  return (
    <ReportPhotoFrame>
      <div className="relative">
        {/* eslint-disable-next-line @next/next/no-img-element -- authenticated blob URL */}
        <img
          src={photoUrl}
          alt="Your uploaded photo with the symmetry axis and mirrored points marked"
          className="block h-auto w-full object-contain"
        />
        <svg
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          className="pointer-events-none absolute inset-0 size-full"
          aria-hidden
        >
          <line
            x1={axisX * 100}
            y1={0}
            x2={axisX * 100}
            y2={100}
            stroke={meridian.accent.secondary}
            strokeWidth={0.3}
            strokeDasharray="1.5 1"
          />
          {pairs.map((pair) => (
            <g key={pair.feature}>
              <line
                x1={pair.left[0] * 100}
                y1={pair.left[1] * 100}
                x2={pair.right[0] * 100}
                y2={pair.right[1] * 100}
                stroke={meridian.accent.secondary}
                strokeWidth={0.25}
                opacity={0.6}
              />
              <circle cx={pair.left[0] * 100} cy={pair.left[1] * 100} r={0.7} fill={meridian.accent.primary} />
              <circle cx={pair.right[0] * 100} cy={pair.right[1] * 100} r={0.7} fill={meridian.accent.primary} />
            </g>
          ))}
        </svg>
      </div>
    </ReportPhotoFrame>
  )
}
