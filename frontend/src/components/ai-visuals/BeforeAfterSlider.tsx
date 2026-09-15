"use client"

import { ChevronsLeftRight } from "lucide-react"
import { useCallback, useRef, useState } from "react"

/**
 * Draggable before/after comparison -- bespoke pointer-drag component, no
 * new npm dependency (same "build the small interactive primitive
 * ourselves" call already made for the report page's SVG overlays).
 * Drag left/right anywhere on the image, not just the handle.
 */
export function BeforeAfterSlider({
  beforeUrl,
  afterUrl,
  beforeLabel = "Before",
  afterLabel = "After",
}: {
  beforeUrl: string
  afterUrl: string
  beforeLabel?: string
  afterLabel?: string
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [position, setPosition] = useState(50)

  const updateFromClientX = useCallback((clientX: number) => {
    const el = containerRef.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const pct = ((clientX - rect.left) / rect.width) * 100
    setPosition(Math.min(100, Math.max(0, pct)))
  }, [])

  function handlePointerDown(event: React.PointerEvent<HTMLDivElement>) {
    event.currentTarget.setPointerCapture(event.pointerId)
    updateFromClientX(event.clientX)
  }

  function handlePointerMove(event: React.PointerEvent<HTMLDivElement>) {
    if (event.buttons !== 1) return
    updateFromClientX(event.clientX)
  }

  return (
    <div
      ref={containerRef}
      className="relative aspect-[4/5] w-full touch-none overflow-hidden rounded-xl bg-muted select-none"
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
    >
      {/* eslint-disable-next-line @next/next/no-img-element -- authenticated blob URL */}
      <img
        src={beforeUrl}
        alt={beforeLabel}
        draggable={false}
        className="absolute inset-0 size-full object-cover"
      />
      <div className="absolute inset-0 overflow-hidden" style={{ clipPath: `inset(0 ${100 - position}% 0 0)` }}>
        {/* eslint-disable-next-line @next/next/no-img-element -- authenticated blob URL */}
        <img
          src={afterUrl}
          alt={afterLabel}
          draggable={false}
          className="absolute inset-0 size-full object-cover"
        />
      </div>

      <div className="pointer-events-none absolute inset-y-0 w-0.5 bg-background" style={{ left: `${position}%` }}>
        <div className="absolute top-1/2 left-1/2 flex size-8 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-background shadow-md">
          <ChevronsLeftRight className="size-4 text-muted-foreground" aria-hidden />
        </div>
      </div>

      <span className="absolute top-2.5 left-2.5 rounded-md bg-foreground/70 px-2 py-0.5 text-[10px] font-semibold tracking-wide text-background uppercase">
        {beforeLabel}
      </span>
      <span className="absolute top-2.5 right-2.5 rounded-md bg-foreground/70 px-2 py-0.5 text-[10px] font-semibold tracking-wide text-background uppercase">
        {afterLabel}
      </span>
    </div>
  )
}
