"use client"

import { motion } from "motion/react"

import { cn } from "@/lib/utils"

/** Facial landmark positions in a 200×240 viewBox (approximate MediaPipe layout). */
const LANDMARKS = [
  { x: 100, y: 28 },
  { x: 58, y: 48 },
  { x: 142, y: 48 },
  { x: 42, y: 95 },
  { x: 158, y: 95 },
  { x: 48, y: 150 },
  { x: 152, y: 150 },
  { x: 70, y: 195 },
  { x: 130, y: 195 },
  { x: 100, y: 212 },
  { x: 72, y: 98 },
  { x: 88, y: 98 },
  { x: 112, y: 98 },
  { x: 128, y: 98 },
  { x: 68, y: 82 },
  { x: 90, y: 78 },
  { x: 110, y: 78 },
  { x: 132, y: 82 },
  { x: 100, y: 110 },
  { x: 100, y: 138 },
  { x: 88, y: 148 },
  { x: 112, y: 148 },
  { x: 78, y: 168 },
  { x: 100, y: 164 },
  { x: 122, y: 168 },
  { x: 100, y: 178 },
] as const

const MESH_LINES: [number, number][] = [
  [10, 11],
  [12, 13],
  [14, 15],
  [16, 17],
  [18, 19],
  [19, 20],
  [19, 21],
  [22, 23],
  [23, 24],
  [23, 25],
  [0, 1],
  [0, 2],
  [1, 3],
  [2, 4],
  [3, 5],
  [4, 6],
  [5, 7],
  [6, 8],
  [7, 9],
  [8, 9],
  [10, 18],
  [13, 18],
]

type Tone = "onBrand" | "onLight"

/**
 * Decorative CV-style face scan. `onBrand` = white strokes for primary panels;
 * `onLight` = primary-tinted strokes for light dashboard surfaces.
 */
export function FacialScanVisual({
  className,
  tone = "onBrand",
}: {
  className?: string
  tone?: Tone
}) {
  const isBrand = tone === "onBrand"
  const strokeId = `scan-stroke-${tone}`
  const beamId = `scan-beam-${tone}`
  const ink = isBrand ? "white" : "var(--primary)"
  const glowClass = isBrand ? "bg-white/20" : "bg-primary/15"
  const meshOpacity = isBrand ? 0.28 : 0.22
  const labelOpacity = isBrand ? 0.75 : 0.65

  return (
    <div className={cn(className)} aria-hidden>
      <div className="relative mx-auto aspect-[5/6] h-full max-h-full w-auto">
        <motion.div
          className={cn("absolute inset-6 rounded-full blur-3xl", glowClass)}
          animate={{ opacity: [0.35, 0.55, 0.35], scale: [0.95, 1.05, 0.95] }}
          transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
        />

        <svg viewBox="0 0 200 240" className="relative h-full w-full overflow-visible" fill="none">
          <defs>
            <linearGradient id={strokeId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={ink} stopOpacity="0.95" />
              <stop offset="100%" stopColor={ink} stopOpacity="0.4" />
            </linearGradient>
            <linearGradient id={beamId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={ink} stopOpacity="0" />
              <stop offset="50%" stopColor={ink} stopOpacity={isBrand ? 0.55 : 0.28} />
              <stop offset="100%" stopColor={ink} stopOpacity="0" />
            </linearGradient>
          </defs>

          <g stroke={ink} strokeWidth="1.5" strokeLinecap="round" opacity="0.7">
            <path d="M28 48 H48 M28 48 V68" />
            <path d="M172 48 H152 M172 48 V68" />
            <path d="M28 192 H48 M28 192 V172" />
            <path d="M172 192 H152 M172 192 V172" />
          </g>

          <motion.ellipse
            cx="100"
            cy="120"
            rx="58"
            ry="78"
            stroke={`url(#${strokeId})`}
            strokeWidth="1.25"
            initial={{ pathLength: 0, opacity: 0 }}
            animate={{ pathLength: 1, opacity: 0.85 }}
            transition={{ duration: 1.4, ease: "easeOut" }}
          />

          <g stroke={ink} strokeWidth="0.6" opacity={meshOpacity}>
            {MESH_LINES.map(([a, b]) => (
              <line
                key={`${a}-${b}`}
                x1={LANDMARKS[a].x}
                y1={LANDMARKS[a].y}
                x2={LANDMARKS[b].x}
                y2={LANDMARKS[b].y}
              />
            ))}
          </g>

          {LANDMARKS.map((point, index) => (
            <motion.circle
              key={`${point.x}-${point.y}-${index}`}
              cx={point.x}
              cy={point.y}
              r="2.2"
              fill={ink}
              initial={{ opacity: 0, scale: 0 }}
              animate={{ opacity: [0.45, 1, 0.45], scale: [0.85, 1.15, 0.85] }}
              transition={{
                duration: 2.4,
                delay: 0.4 + index * 0.04,
                repeat: Infinity,
                ease: "easeInOut",
              }}
            />
          ))}

          <motion.rect
            x="36"
            width="128"
            height="36"
            fill={`url(#${beamId})`}
            initial={{ y: 40 }}
            animate={{ y: [40, 170, 40] }}
            transition={{ duration: 4.5, repeat: Infinity, ease: "easeInOut" }}
          />
          <motion.line
            x1="40"
            x2="160"
            stroke={ink}
            strokeWidth="1.5"
            strokeLinecap="round"
            initial={{ y1: 58, y2: 58, opacity: 0.9 }}
            animate={{ y1: [58, 188, 58], y2: [58, 188, 58], opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 4.5, repeat: Infinity, ease: "easeInOut" }}
          />

          <motion.g
            initial={{ opacity: 0 }}
            animate={{ opacity: [0.4, 0.9, 0.4] }}
            transition={{ duration: 3, repeat: Infinity, ease: "easeInOut", delay: 0.6 }}
          >
            <line x1="158" y1="98" x2="186" y2="98" stroke={ink} strokeWidth="0.8" opacity="0.55" />
            <text x="188" y="101" fill={ink} fontSize="8" opacity={labelOpacity} fontFamily="var(--font-geist-sans), ui-sans-serif, system-ui">
              eyes
            </text>
            <line x1="158" y1="148" x2="186" y2="148" stroke={ink} strokeWidth="0.8" opacity="0.55" />
            <text x="188" y="151" fill={ink} fontSize="8" opacity={labelOpacity} fontFamily="var(--font-geist-sans), ui-sans-serif, system-ui">
              nose
            </text>
            <line x1="14" y1="168" x2="42" y2="168" stroke={ink} strokeWidth="0.8" opacity="0.55" />
            <text x="4" y="171" fill={ink} fontSize="8" opacity={labelOpacity} fontFamily="var(--font-geist-sans), ui-sans-serif, system-ui">
              lips
            </text>
          </motion.g>
        </svg>
      </div>
    </div>
  )
}
