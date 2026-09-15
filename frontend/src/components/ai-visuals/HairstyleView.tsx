"use client"

import { Loader2, RotateCcw, Sparkles } from "lucide-react"

import { VariationGallery } from "./VariationGallery"
import { useAiVisualKind } from "./useAiVisualKind"
import { useFrontPhotoUrl } from "@/hooks/useFrontPhotoUrl"
import { Button } from "@/components/ui/button"

export function HairstyleView() {
  const photoUrl = useFrontPhotoUrl()
  const { variations, errorMessage, isRetrying, retry, canRetry } = useAiVisualKind("hairstyle")

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
            Hairstyle previews
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Hairstyle recommendations based on face shape, hairline, and overall facial balance.
          </p>
        </div>
        {canRetry ? (
          <Button type="button" variant="outline" size="sm" onClick={() => void retry()} disabled={isRetrying}>
            {isRetrying ? <Loader2 className="size-3.5 animate-spin" /> : <RotateCcw className="size-3.5" />}
            Retry generation
          </Button>
        ) : null}
      </div>
      <VariationGallery kind="hairstyle" beforePhotoUrl={photoUrl} variations={variations} />
    </div>
  )
}
