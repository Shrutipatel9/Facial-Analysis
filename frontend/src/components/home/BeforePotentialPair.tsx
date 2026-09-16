"use client"

import { ImageOff, Loader2, RotateCcw } from "lucide-react"
import { useEffect, useRef, useState } from "react"

import { useAiVisualKind } from "../ai-visuals/useAiVisualKind"
import { Button } from "@/components/ui/button"
import { useFrontPhotoUrl } from "@/hooks/useFrontPhotoUrl"
import * as aiVisualsApi from "@/lib/aiVisuals/aiVisualsApi"

/**
 * Home Overview Before/Potential pair (spec §1.4) -- center column hero.
 * Potential is a single whole-face AI "after" image (kind="potential",
 * see Backend/app/services/ai_visual_service.py's _build_potential_rows) --
 * added 2026-09-18, previously a permanent empty state. Reuses the exact
 * same create/poll/retry hook HairstyleView/OutfitView/AgingView already
 * use (useAiVisualKind), and the same single-image blob-fetch technique
 * frontend/src/components/report/ui/BeforeAfterBlock.tsx already uses for
 * a per-feature generated image.
 */
export function BeforePotentialPair() {
  const frontPhotoUrl = useFrontPhotoUrl()
  const { variations, errorMessage, isRetrying, retry, canRetry } = useAiVisualKind("potential")
  const potential = variations?.[0]

  const [potentialUrl, setPotentialUrl] = useState<string | null>(null)
  const fetchedFor = useRef<string | null>(null)

  useEffect(() => {
    if (!potential || potential.status !== "generated") return
    if (fetchedFor.current === potential.id) return
    fetchedFor.current = potential.id

    // No cancelled-flag guard on the setPotentialUrl call itself -- same
    // fetchedFor-ref-blocks-the-double-run convention as BeforeAfterBlock.tsx.
    let objectUrl: string | null = null
    aiVisualsApi
      .getVisualImage("potential", potential.id)
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob)
        setPotentialUrl(objectUrl)
      })
      .catch(() => {})

    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [potential])

  return (
    <div className="grid h-fit w-full grid-cols-2 gap-3">
      <figure className="m-0 overflow-hidden rounded-2xl border border-border/80 bg-card shadow-[0_10px_30px_-18px_rgba(20,55,75,0.28)]">
        {frontPhotoUrl ? (
          // eslint-disable-next-line @next/next/no-img-element -- authenticated blob URL
          <img
            src={frontPhotoUrl}
            alt="Before — your validated front photo"
            className="block aspect-[3/4] w-full object-cover"
          />
        ) : (
          <div className="flex aspect-[3/4] items-center justify-center bg-muted/40">
            <Loader2 className="size-5 animate-spin text-muted-foreground/60" aria-hidden />
          </div>
        )}
        <figcaption className="py-2 text-center text-[11px] font-semibold tracking-[0.1em] text-muted-foreground uppercase">
          Before
        </figcaption>
      </figure>

      <figure className="m-0 overflow-hidden rounded-2xl border border-border/80 bg-card shadow-[0_10px_30px_-18px_rgba(20,55,75,0.28)]">
        {potentialUrl ? (
          // eslint-disable-next-line @next/next/no-img-element -- authenticated blob URL
          <img
            src={potentialUrl}
            alt="Potential — AI-generated whole-face preview"
            className="block aspect-[3/4] w-full object-cover"
          />
        ) : errorMessage || potential?.status === "failed" ? (
          <div className="flex aspect-[3/4] flex-col items-center justify-center gap-2 bg-muted/35 px-4 text-center">
            <ImageOff className="size-5 text-muted-foreground/60" aria-hidden />
            <p className="text-xs leading-snug text-muted-foreground">
              {errorMessage ?? "The potential preview couldn't be generated."}
            </p>
            {canRetry ? (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => void retry()}
                disabled={isRetrying}
              >
                {isRetrying ? <Loader2 className="size-3.5 animate-spin" /> : <RotateCcw className="size-3.5" />}
                Try again
              </Button>
            ) : null}
          </div>
        ) : (
          <div className="flex aspect-[3/4] flex-col items-center justify-center gap-2 bg-muted/35 px-4 text-center">
            <Loader2 className="size-5 animate-spin text-muted-foreground/60" aria-hidden />
            <p className="text-xs leading-snug text-muted-foreground">Generating your potential preview…</p>
          </div>
        )}
        <figcaption className="py-2 text-center text-[11px] font-semibold tracking-[0.1em] text-muted-foreground uppercase">
          Potential
        </figcaption>
      </figure>
    </div>
  )
}
