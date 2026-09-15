"use client"

import { useEffect, useRef, useState } from "react"

import { BeforeAfterSlider } from "./BeforeAfterSlider"
import { Badge } from "@/components/ui/badge"
import * as aiVisualsApi from "@/lib/aiVisuals/aiVisualsApi"
import type { AiVisual, AiVisualKind } from "@/lib/aiVisuals/aiVisualsApi"

/**
 * Shared hairstyle/outfit gallery matching screenshot: portrait slider +
 * circular thumbs + right detail panel (RECOMMENDED / attributes / EXPLANATION).
 */
export function VariationGallery({
  kind,
  beforePhotoUrl,
  variations,
}: {
  kind: AiVisualKind
  beforePhotoUrl: string | null
  variations: AiVisual[]
}) {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [imageUrls, setImageUrls] = useState<Record<string, string>>({})
  const objectUrlsRef = useRef<string[]>([])

  useEffect(() => {
    const objectUrls = objectUrlsRef.current
    return () => {
      objectUrls.forEach((url) => URL.revokeObjectURL(url))
    }
  }, [])

  useEffect(() => {
    const newlyGenerated = variations.filter((variation) => variation.status === "generated" && !(variation.id in imageUrls))
    if (newlyGenerated.length === 0) return

    Promise.all(
      newlyGenerated.map(async (variation) => {
        try {
          const blob = await aiVisualsApi.getVisualImage(kind, variation.id)
          const url = URL.createObjectURL(blob)
          objectUrlsRef.current.push(url)
          return [variation.id, url] as const
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
    // eslint-disable-next-line react-hooks/exhaustive-deps -- imageUrls is read only to compute the delta; including it would just re-run this same no-op check
  }, [variations, kind])

  const selected = variations.find((variation) => variation.id === selectedId) ?? variations[0]

  if (!selected) return null

  const selectedImageUrl = imageUrls[selected.id]

  function openEnlarge() {
    if (!selectedImageUrl) return
    window.open(selectedImageUrl, "_blank", "noopener,noreferrer")
  }

  return (
    <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)] xl:grid-cols-[minmax(0,26rem)_minmax(0,1fr)]">
      <div className="space-y-2">
        {selectedImageUrl && beforePhotoUrl ? (
          <div className="mx-auto w-full max-w-[26rem]">
            <BeforeAfterSlider beforeUrl={beforePhotoUrl} afterUrl={selectedImageUrl} />
          </div>
        ) : (
          <div className="mx-auto flex aspect-[4/5] w-full max-w-[26rem] items-center justify-center rounded-xl bg-muted text-sm text-muted-foreground">
            {selected.status === "failed"
              ? "This preview couldn't be generated."
              : "Generating your preview…"}
          </div>
        )}

        {selectedImageUrl ? (
          <button
            type="button"
            onClick={openEnlarge}
            className="text-sm font-medium text-primary hover:underline"
          >
            Click to enlarge
          </button>
        ) : null}

        <div className="flex gap-2 overflow-x-auto pt-1 pb-1">
          {variations.map((variation) => {
            const thumbUrl = imageUrls[variation.id]
            const isActive = variation.id === selected.id
            return (
              <button
                key={variation.id}
                type="button"
                onClick={() => setSelectedId(variation.id)}
                className={`relative size-14 shrink-0 overflow-hidden rounded-full border-2 transition-colors ${
                  isActive ? "border-primary" : "border-transparent opacity-75 hover:opacity-100"
                }`}
                aria-label={variation.name ?? "Variation"}
              >
                {thumbUrl ? (
                  // eslint-disable-next-line @next/next/no-img-element -- authenticated blob URL
                  <img src={thumbUrl} alt="" className="size-full object-cover" />
                ) : (
                  <div className="flex size-full items-center justify-center bg-muted text-[10px] text-muted-foreground">
                    {variation.status === "failed" ? "!" : "…"}
                  </div>
                )}
              </button>
            )
          })}
        </div>
      </div>

      <div className="min-w-0 space-y-5 pt-0.5">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-[11px] font-semibold tracking-[0.14em] text-muted-foreground uppercase">
              Recommended
            </p>
            {selected.is_recommended ? (
              <Badge variant="outline" className="rounded-full border-primary/45 px-2.5 py-0.5 text-[10px] font-semibold tracking-wide text-primary uppercase">
                FaceIQ choice
              </Badge>
            ) : null}
          </div>
          <h3 className="text-2xl font-semibold tracking-tight text-foreground">{selected.name}</h3>
        </div>

        {selected.attributes ? (
          <dl className="grid grid-cols-2 gap-2.5">
            {Object.entries(selected.attributes).map(([key, value]) => (
              <div key={key} className="rounded-xl border border-border px-3.5 py-3">
                <dt className="text-[10px] font-semibold tracking-[0.14em] text-muted-foreground uppercase">
                  {key}
                </dt>
                <dd className="mt-1 text-sm font-semibold text-foreground">{String(value)}</dd>
              </div>
            ))}
          </dl>
        ) : null}

        {selected.explanation ? (
          <div className="space-y-1.5">
            <p className="text-[11px] font-semibold tracking-[0.14em] text-muted-foreground uppercase">
              Explanation
            </p>
            <p className="text-sm leading-relaxed text-muted-foreground">{selected.explanation}</p>
          </div>
        ) : null}
      </div>
    </div>
  )
}
