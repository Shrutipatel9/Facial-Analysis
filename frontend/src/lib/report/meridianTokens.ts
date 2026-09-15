/**
 * Meridian report visual token system (docs/report_design_spec.md §1),
 * applied narrowly to report cards -- not as a full-page ivory wash. The
 * outer app shell keeps its own teal-neutral surface; everything inside a
 * report/dashboard card below draws from these tokens only.
 *
 * Previously an ad hoc partial object inline in ReportScreen.tsx (card/ink/
 * inkMuted/accent/accentSecondary/recessed). This is the full set from the
 * spec's token table, including surface.paper and the 3 state.* tokens the
 * inline version never had.
 */
export const meridian = {
  ink: {
    primary: "#2B2822",
    muted: "#6B6558",
  },
  surface: {
    paper: "#FAF7F1",
    card: "#FFFFFF",
    recessed: "#EFEAE0",
  },
  accent: {
    primary: "#A8461F",
    secondary: "#3E6E64",
  },
  state: {
    positive: "#5C7A52",
    notice: "#B98A3E",
    reserved: "#96432E",
  },
} as const

/**
 * Confidence Indicator glyph (§1's icon library rule -- one shape family,
 * reused everywhere a driver/finding needs a confidence signal).
 */
export type ConfidenceLevel = "high" | "medium" | "low"

export function confidenceGlyph(level: ConfidenceLevel): string {
  switch (level) {
    case "high":
      return "●"
    case "medium":
      return "◐"
    case "low":
      return "○"
  }
}

/**
 * Maps a 0-100 score to a qualitative state tone -- never used for the
 * Alert/Flag Card's `state.reserved`, which is reserved exclusively for a
 * professional-referral framing (§15.2), not a low score.
 */
export function scoreStateTone(score: number): string {
  if (score >= 65) return meridian.state.positive
  if (score >= 40) return meridian.state.notice
  return meridian.ink.muted
}
