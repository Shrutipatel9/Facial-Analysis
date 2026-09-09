"use client"

import { ArrowRight, Check, Loader2, RotateCcw } from "lucide-react"

import { Button } from "@/components/ui/button"
import type { PhotoAngleStatus } from "@/lib/photos/photoApi"

interface PhotoSetCompleteStepProps {
  angles: PhotoAngleStatus[]
  isContinuing: boolean
  onContinue: () => void
  onChangePhoto: (angleId: string) => void
}

/**
 * Shown once every required angle has a passed photo, replacing the
 * per-angle capture view -- deliberately a distinct confirmation step, not
 * an automatic redirect, so completing the set doesn't yank the user away
 * before they see their own result (see usePhotoUploadGuard.ts's
 * docstring for the guard-side half of this fix).
 *
 * Each angle offers Change so the user can retake before Continue
 * (payment locks further photo changes server-side).
 */
export function PhotoSetCompleteStep({
  angles,
  isContinuing,
  onContinue,
  onChangePhoto,
}: PhotoSetCompleteStepProps) {
  return (
    <div className="mx-auto flex w-full max-w-xl flex-1 flex-col items-center justify-center gap-8 px-2 py-10 text-center">
      <span className="flex size-14 items-center justify-center rounded-full bg-success/15 text-success">
        <Check className="size-6" strokeWidth={3} aria-hidden />
      </span>

      <div className="space-y-1.5">
        <h1 className="font-sans text-3xl font-semibold tracking-tight sm:text-4xl">All photos submitted</h1>
        <p className="text-base leading-relaxed text-muted-foreground">
          Every required angle passed. Change any photo below if you need to, then continue when you&apos;re
          ready.
        </p>
      </div>

      <ul className="grid w-full grid-cols-1 gap-3 sm:grid-cols-3">
        {angles.map((angle) => (
          <li
            key={angle.angle}
            className="flex flex-row items-center justify-between gap-3 rounded-xl border border-success/30 bg-success/5 px-4 py-3 text-left sm:flex-col sm:items-stretch sm:gap-3"
          >
            <div className="flex items-center justify-between gap-2 sm:w-full">
              <span className="text-sm font-medium">{angle.label}</span>
              <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-success/15 text-success">
                <Check className="size-3" strokeWidth={3} aria-hidden />
              </span>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-8 shrink-0 rounded-full px-3 text-xs"
              disabled={isContinuing}
              onClick={() => onChangePhoto(angle.angle)}
            >
              <RotateCcw className="size-3" />
              Retake
            </Button>
          </li>
        ))}
      </ul>

      <Button type="button" className="h-11 w-48 rounded-full" onClick={onContinue} disabled={isContinuing}>
        {isContinuing ? <Loader2 className="size-4 animate-spin" /> : null}
        Continue
        <ArrowRight />
      </Button>
    </div>
  )
}
