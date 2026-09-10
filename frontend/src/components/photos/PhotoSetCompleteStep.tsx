"use client"

import { AlertTriangle, ArrowRight, Check, Loader2, RotateCcw } from "lucide-react"

import { Button } from "@/components/ui/button"
import type { IdentityCheck, PhotoAngleStatus } from "@/lib/photos/photoApi"
import { cn } from "@/lib/utils"

interface PhotoSetCompleteStepProps {
  angles: PhotoAngleStatus[]
  isContinuing: boolean
  identityCheck: IdentityCheck | null
  onContinue: () => void
  onChangePhoto: (angleId: string) => void
}

/**
 * Shown once every required angle has a passed photo. `identityCheck` is
 * the cross-photo same-person result from GET /photos/status. While it is
 * null the store is mid-refetch after a retake — treat that as pending
 * (not "consistent"), so cards don't flash green and Continue stays off.
 *
 * Mismatched angles come from ArcFace embedding vote on the backend with
 * no preferred reference angle — whichever photo(s) match the fewest
 * others are flagged.
 */
export function PhotoSetCompleteStep({
  angles,
  isContinuing,
  identityCheck,
  onContinue,
  onChangePhoto,
}: PhotoSetCompleteStepProps) {
  const isCheckingIdentity = identityCheck === null
  const mismatchedAngles = identityCheck?.consistent === false ? identityCheck.mismatched_angles : []
  const hasMismatch = mismatchedAngles.length > 0
  const canContinue = identityCheck?.consistent === true

  return (
    <div className="mx-auto flex w-full max-w-xl flex-1 flex-col items-center justify-center gap-8 px-2 py-10 text-center">
      <span
        className={cn(
          "flex size-14 items-center justify-center rounded-full",
          isCheckingIdentity
            ? "bg-primary/10 text-primary"
            : hasMismatch
              ? "bg-destructive/15 text-destructive"
              : "bg-success/15 text-success"
        )}
      >
        {isCheckingIdentity ? (
          <Loader2 className="size-6 animate-spin" aria-hidden />
        ) : hasMismatch ? (
          <AlertTriangle className="size-6" strokeWidth={2.25} aria-hidden />
        ) : (
          <Check className="size-6" strokeWidth={3} aria-hidden />
        )}
      </span>

      <div className="space-y-1.5">
        <h1 className="font-sans text-3xl font-semibold tracking-tight sm:text-4xl">
          {isCheckingIdentity
            ? "Checking your photos"
            : hasMismatch
              ? mismatchedAngles.length > 1
                ? "These photos don't match"
                : "One photo doesn't match"
              : "All photos submitted"}
        </h1>
        <p className="text-base leading-relaxed text-muted-foreground">
          {isCheckingIdentity
            ? "Making sure all three angles show the same person…"
            : (identityCheck?.message ??
              "Every required angle passed. Change any photo below if you need to, then continue when you're ready.")}
        </p>
      </div>

      <ul className="grid w-full grid-cols-1 gap-3 sm:grid-cols-3">
        {angles.map((angle) => {
          const isOdd = mismatchedAngles.includes(angle.angle)
          return (
            <li
              key={angle.angle}
              className={cn(
                "flex flex-row items-center justify-between gap-3 rounded-xl border px-4 py-3 text-left sm:flex-col sm:items-stretch sm:gap-3",
                isCheckingIdentity
                  ? "border-border/60 bg-muted/30"
                  : isOdd
                    ? "border-destructive/40 bg-destructive/5"
                    : "border-success/30 bg-success/5"
              )}
            >
              <div className="flex items-center justify-between gap-2 sm:w-full">
                <span className="text-sm font-medium">{angle.label}</span>
                <span
                  className={cn(
                    "flex size-5 shrink-0 items-center justify-center rounded-full",
                    isCheckingIdentity
                      ? "bg-muted text-muted-foreground"
                      : isOdd
                        ? "bg-destructive/15 text-destructive"
                        : "bg-success/15 text-success"
                  )}
                >
                  {isCheckingIdentity ? (
                    <Loader2 className="size-3 animate-spin" aria-hidden />
                  ) : isOdd ? (
                    <AlertTriangle className="size-3" strokeWidth={2.5} aria-hidden />
                  ) : (
                    <Check className="size-3" strokeWidth={3} aria-hidden />
                  )}
                </span>
              </div>
              {isOdd ? <p className="text-xs text-destructive">Doesn&apos;t match your other photos</p> : null}
              <Button
                type="button"
                variant={isOdd ? "destructive" : "outline"}
                size="sm"
                className="h-8 shrink-0 rounded-full px-3 text-xs"
                disabled={isContinuing || isCheckingIdentity}
                onClick={() => onChangePhoto(angle.angle)}
              >
                <RotateCcw className="size-3" />
                Retake
              </Button>
            </li>
          )
        })}
      </ul>

      <Button
        type="button"
        className="h-11 w-48 rounded-full"
        onClick={onContinue}
        disabled={isContinuing || !canContinue}
      >
        {isContinuing || isCheckingIdentity ? <Loader2 className="size-4 animate-spin" /> : null}
        Continue
        <ArrowRight />
      </Button>
      {hasMismatch ? (
        <p className="-mt-4 text-xs text-muted-foreground">
          {mismatchedAngles.length > 1
            ? "Retake the flagged photos above to continue."
            : "Retake the flagged photo above to continue."}
        </p>
      ) : null}
    </div>
  )
}
