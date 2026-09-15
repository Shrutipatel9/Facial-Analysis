"use client"

import { ImageOff, Loader2 } from "lucide-react"

import { useFrontPhotoUrl } from "@/hooks/useFrontPhotoUrl"

/**
 * Home Overview Before/Potential pair (spec §1.4) -- center column hero.
 * Potential stays an honest empty state until whole-face generation exists.
 */
export function BeforePotentialPair() {
  const frontPhotoUrl = useFrontPhotoUrl()

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
        <div className="flex aspect-[3/4] flex-col items-center justify-center gap-2 bg-muted/35 px-4 text-center">
          <ImageOff className="size-5 text-muted-foreground/60" aria-hidden />
          <p className="text-xs leading-snug text-muted-foreground">
            Whole-face potential preview isn&apos;t available yet.
          </p>
        </div>
        <figcaption className="py-2 text-center text-[11px] font-semibold tracking-[0.1em] text-muted-foreground uppercase">
          Potential
        </figcaption>
      </figure>
    </div>
  )
}
