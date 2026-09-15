import { meridian } from "@/lib/report/meridianTokens"

const STAGES = [1, 2, 3, 4, 5, 6, 7] as const

/**
 * Hair page's illustrated 7-stage strip (report_design_spec.md v3.0
 * §13.3), "Normal" -> "Need Attention" -> "Extreme". The only illustrated
 * (non-photographic, non-chart) component in the report -- a small inline
 * SVG head-with-hairline glyph per stage (no external asset dependency),
 * recession level increasing left-to-right with the stage number. The
 * subject's current stage is boxed/highlighted with an accent border.
 */
export function HairLossScale({ stage, label }: { stage: number; label: string }) {
  return (
    <div className="space-y-2">
      <div className="flex items-end justify-between gap-1.5">
        {STAGES.map((value) => (
          <div
            key={value}
            className="flex flex-1 flex-col items-center gap-1 rounded-lg border px-1 py-1.5"
            style={{
              borderColor: value === stage ? meridian.accent.primary : "transparent",
              backgroundColor: value === stage ? meridian.surface.recessed : "transparent",
            }}
          >
            <HairLossIcon recession={value} />
            <span className="text-[10px] tabular-nums" style={{ color: meridian.ink.muted }}>
              {value}
            </span>
          </div>
        ))}
      </div>
      <div className="flex justify-between text-[11px]" style={{ color: meridian.ink.muted }}>
        <span>Normal</span>
        <span>Need Attention</span>
        <span>Extreme</span>
      </div>
      <p className="text-sm" style={{ color: meridian.ink.primary }}>
        Stage {stage} of 7 — {label}
      </p>
    </div>
  )
}

/** `recession` 1-7: higher = the hairline/crown outline sits further back. */
function HairLossIcon({ recession }: { recession: number }) {
  const recede = ((recession - 1) / 6) * 5 // 0..5px the hairline arc pulls back by
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="13" r="8" stroke={meridian.ink.muted} strokeWidth="1.2" />
      <path
        d={`M 4.5 ${11 - recede * 0.3} A 7.5 7.5 0 0 1 19.5 ${11 - recede * 0.3}`}
        stroke={meridian.accent.primary}
        strokeWidth="1.4"
        strokeLinecap="round"
        fill="none"
      />
    </svg>
  )
}
