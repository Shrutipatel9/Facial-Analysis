import { Progress } from "@/components/ui/progress"

interface ProgressBarProps {
  /** Display number 1–23, or 24 for disclaimer (clamped for the bar). */
  current: number
}

const TOTAL_QUESTIONS = 23

export function ProgressBar({ current }: ProgressBarProps) {
  const clamped = Math.min(current, TOTAL_QUESTIONS)
  const pct = (clamped / TOTAL_QUESTIONS) * 100

  return (
    <div className="space-y-2.5">
      <div className="flex items-end justify-between gap-3">
        <div>
          <p className="text-[11px] font-medium tracking-[0.18em] text-primary/70 uppercase">Progress</p>
          <p className="mt-0.5 text-sm font-medium text-foreground">
            Question {clamped}
            <span className="text-muted-foreground"> / {TOTAL_QUESTIONS}</span>
          </p>
        </div>
        <p className="text-sm font-semibold tabular-nums text-primary">{Math.round(pct)}%</p>
      </div>
      <Progress value={pct} />
    </div>
  )
}
