"use client"

import { Loader2, RotateCcw, Sparkles } from "lucide-react"
import { useEffect, useState } from "react"

import { useAiVisualKind } from "./useAiVisualKind"
import { useFrontPhotoUrl } from "@/hooks/useFrontPhotoUrl"
import { Button } from "@/components/ui/button"
import * as aiVisualsApi from "@/lib/aiVisuals/aiVisualsApi"

const REFERENCE_AGE = 28
const AGING_DISCLAIMER = "* Educational purpose only, not a forecast."

/**
 * Healthy Aging's vertical card stack -- deliberately NOT the shared
 * VariationGallery (no draggable slider, no thumbnail row, no "recommended"
 * concept among fixed age steps). Card 1 is the user's own real photo,
 * never a generated row.
 */
export function AgingView() {
  const photoUrl = useFrontPhotoUrl()
  const { variations, errorMessage, isRetrying, retry, canRetry } = useAiVisualKind("aging")
  const [imageUrls, setImageUrls] = useState<Record<string, string>>({})

  useEffect(() => {
    if (!variations) return
    const newlyGenerated = variations.filter((v) => v.status === "generated" && !(v.id in imageUrls))
    if (newlyGenerated.length === 0) return
    Promise.all(
      newlyGenerated.map(async (variation) => {
        try {
          const blob = await aiVisualsApi.getVisualImage("aging", variation.id)
          return [variation.id, URL.createObjectURL(blob)] as const
        } catch {
          return null
        }
      })
    ).then((results) => {
      setImageUrls((prev) => {
        const next = { ...prev }
        for (const result of results) {
          if (result) next[result[0]] = result[1]
        }
        return next
      })
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps -- imageUrls is read only to compute the delta
  }, [variations])

  if (errorMessage) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-destructive">{errorMessage}</p>
        <Button type="button" variant="outline" size="sm" onClick={() => void retry()} disabled={isRetrying}>
          {isRetrying ? <Loader2 className="size-3.5 animate-spin" /> : <RotateCcw className="size-3.5" />}
          Try again
        </Button>
      </div>
    )
  }

  if (!variations) {
    return (
      <div className="flex flex-1 items-center justify-center py-16">
        <Loader2 className="size-6 animate-spin text-primary/60" aria-label="Loading" />
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="flex items-center gap-2 text-xl font-semibold tracking-tight">
            <Sparkles className="size-5 text-primary" aria-hidden />
            Healthy aging
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Gentle healthy-aging preview, intended for educational visualization only.
          </p>
        </div>
        {canRetry ? (
          <Button type="button" variant="outline" size="sm" onClick={() => void retry()} disabled={isRetrying}>
            {isRetrying ? <Loader2 className="size-3.5 animate-spin" /> : <RotateCcw className="size-3.5" />}
            Retry generation
          </Button>
        ) : null}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <AgingCard label={`Current — ${REFERENCE_AGE} — Reference`} imageUrl={photoUrl} />
        {variations.map((variation) => {
          const ageYears = Number(variation.attributes?.age_years ?? 0)
          const delta = ageYears - REFERENCE_AGE
          return (
            <AgingCard
              key={variation.id}
              label={`+${delta} years — ${ageYears} — ${variation.name}`}
              imageUrl={imageUrls[variation.id]}
              status={variation.status}
              disclaimer={AGING_DISCLAIMER}
            />
          )
        })}
      </div>
    </div>
  )
}

function AgingCard({
  label,
  imageUrl,
  status,
  disclaimer,
}: {
  label: string
  imageUrl: string | null | undefined
  status?: string
  disclaimer?: string
}) {
  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card">
      {imageUrl ? (
        // eslint-disable-next-line @next/next/no-img-element -- authenticated blob URL
        <img src={imageUrl} alt={label} className="aspect-[4/5] w-full object-cover" />
      ) : (
        <div className="flex aspect-[4/5] w-full items-center justify-center bg-muted text-sm text-muted-foreground">
          {status === "failed" ? "This preview couldn't be generated." : status ? "Generating…" : ""}
        </div>
      )}
      <div className="space-y-1 p-3">
        <p className="text-sm font-medium text-foreground">{label}</p>
        {disclaimer ? <p className="text-xs text-muted-foreground">{disclaimer}</p> : null}
      </div>
    </div>
  )
}
