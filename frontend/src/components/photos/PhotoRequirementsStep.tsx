"use client"

import { ArrowRight, Check } from "lucide-react"

import { Button } from "@/components/ui/button"

/** 7-point guideline checklist from FR-005 / docs/photo_capture_spec.md §2. */
const GUIDELINES = [
  "Remove glasses and hat",
  "Use natural, even lighting",
  "Use a plain white background",
  "Tie back long hair",
  "Remove makeup",
  "Avoid neck-covering clothing",
  "Do not use filters",
] as const

interface PhotoRequirementsStepProps {
  onContinue: () => void
}

/**
 * Photo requirements review (FR-005). Text checklist with green ticks —
 * two-up grid, content-width cards (not full-bleed rows).
 */
export function PhotoRequirementsStep({ onContinue }: PhotoRequirementsStepProps) {
  return (
    <div className="w-full space-y-8">
      <header>
        <div>
          <h1 className="font-sans text-4xl font-semibold tracking-tight text-foreground sm:text-5xl sm:leading-[1.1]">
            Photo Requirements
          </h1>
          <p className="mt-0.5 font-sans text-3xl font-normal tracking-tight text-muted-foreground/55 sm:text-4xl sm:leading-[1.15]">
            Confirmation
          </p>
        </div>
        <p className="mt-5 max-w-xl text-base leading-relaxed text-foreground">
          Please review and confirm the following photo guidelines to ensure accurate results.
        </p>
      </header>

      <ul className="grid max-w-3xl grid-cols-1 gap-3 sm:grid-cols-2">
        {GUIDELINES.map((text) => (
          <li
            key={text}
            className="flex items-start gap-2.5 rounded-xl border border-border bg-card px-3.5 py-3 text-base leading-snug text-foreground"
          >
            <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-success/15 text-success">
              <Check className="size-3" strokeWidth={3} aria-hidden />
            </span>
            <span>{text}</span>
          </li>
        ))}
      </ul>

      <div className="flex justify-end pt-1">
        <Button
          type="button"
          className="h-11 w-36 shrink-0 rounded-full sm:w-40"
          onClick={onContinue}
        >
          Continue
          <ArrowRight />
        </Button>
      </div>
    </div>
  )
}
