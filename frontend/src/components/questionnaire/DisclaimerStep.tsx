"use client"

import { Checkbox } from "@/components/ui/checkbox"
import { cn } from "@/lib/utils"

interface DisclaimerStepProps {
  disclaimerText: string
  accepted: boolean
  onAcceptedChange: (accepted: boolean) => void
  error?: string
}

/** Content-only disclaimer card body — nav buttons live outside the card. */
export function DisclaimerStep({
  disclaimerText,
  accepted,
  onAcceptedChange,
  error,
}: DisclaimerStepProps) {
  return (
    <div className="space-y-5">
      <div className="space-y-1.5">
        <p className="text-[11px] font-medium tracking-[0.18em] text-primary/70 uppercase">Almost done</p>
        <h2 className="font-heading text-xl font-semibold tracking-tight sm:text-2xl">
          Review &amp; confirm
        </h2>
      </div>

      <div className="max-h-48 overflow-y-auto rounded-xl border border-border bg-muted/30 p-4 text-sm leading-relaxed text-muted-foreground">
        {disclaimerText}
      </div>

      <label
        className={cn(
          "flex w-full cursor-pointer items-start gap-3 rounded-xl border px-4 py-3.5 text-left text-sm transition",
          accepted ? "border-primary/35 bg-primary/[0.06]" : "border-border hover:border-primary/20"
        )}
      >
        <Checkbox checked={accepted} onCheckedChange={onAcceptedChange} className="mt-0.5" />
        <span className="leading-snug font-medium">I have read and agree to the above.</span>
      </label>
      {error ? <p className="text-sm font-medium text-destructive">{error}</p> : null}
    </div>
  )
}
