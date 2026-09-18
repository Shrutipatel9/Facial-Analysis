import { Badge } from "@/components/ui/badge"
import { meridian } from "@/lib/report/meridianTokens"
import type { RecommendationItem } from "@/lib/reports/reportApi"

// FR-025/FR-024 (Milestone 3) -- difficulty and risk_level both drive a
// colored badge from the same 3-tier severity scale (Easy/Low -> positive,
// Medium -> notice, Hard/High -> accent.primary), so one shared mapping
// covers both fields rather than two near-duplicate ones. `state.reserved`
// is deliberately excluded: meridianTokens.ts's own doc comment reserves
// it "exclusively for a professional-referral framing," not a severity
// read, even for risk_level="High" where that framing might seem to fit.
export function severityColor(value: "Easy" | "Medium" | "Hard" | "Low" | "High"): string {
  if (value === "Easy" || value === "Low") return meridian.state.positive
  if (value === "Medium") return meridian.state.notice
  return meridian.accent.primary
}

export function MetaBadge({ children, color }: { children: string; color: string }) {
  return (
    <Badge
      variant="outline"
      className="rounded-full px-2.5 py-0.5 text-[10px] font-semibold tracking-wide uppercase"
      style={{ borderColor: `${color}66`, color }}
    >
      {children}
    </Badge>
  )
}

/**
 * One Treatment Protocol / Report Protocol recommendation line item
 * (FR-025) -- shared by TreatmentProtocolPanel (Home Overview) and
 * ProtocolSection (Report page) so the badge row is defined once, not
 * reimplemented per surface. Renders `item.text` plus a wrapped row of
 * small outline badges for whichever of cadence/time-to-effect/cost/
 * difficulty the AI confidently supplied -- a null field is simply
 * omitted, never rendered as a placeholder ("—"/"N/A").
 */
export function ProtocolItemRow({ item }: { item: RecommendationItem }) {
  const hasMeta = Boolean(
    item.cadence || item.time_to_effect || item.cost || item.difficulty || item.category || item.risk_level || item.product_or_method
  )

  return (
    <li className="space-y-1.5">
      <p className="text-sm leading-relaxed" style={{ color: meridian.ink.muted }}>
        {item.text}
      </p>
      {hasMeta ? (
        <div className="flex flex-wrap gap-1.5">
          {item.cadence ? <MetaBadge color={meridian.accent.secondary}>{item.cadence}</MetaBadge> : null}
          {item.time_to_effect ? <MetaBadge color={meridian.accent.secondary}>{item.time_to_effect}</MetaBadge> : null}
          {item.cost ? <MetaBadge color={meridian.accent.secondary}>{item.cost}</MetaBadge> : null}
          {item.difficulty ? <MetaBadge color={severityColor(item.difficulty)}>{item.difficulty}</MetaBadge> : null}
          {item.category ? <MetaBadge color={meridian.accent.secondary}>{item.category}</MetaBadge> : null}
          {item.risk_level ? (
            <MetaBadge color={severityColor(item.risk_level)}>{`${item.risk_level} risk`}</MetaBadge>
          ) : null}
          {item.product_or_method ? (
            <MetaBadge color={meridian.accent.secondary}>{item.product_or_method}</MetaBadge>
          ) : null}
        </div>
      ) : null}
    </li>
  )
}
