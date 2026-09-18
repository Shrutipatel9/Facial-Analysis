"use client"

import { motion } from "motion/react"

import { ProtocolItemRow } from "@/components/report/ui/ProtocolItemRow"
import { meridian } from "@/lib/report/meridianTokens"
import type { ReportFullContent } from "@/lib/reports/reportApi"

// FR-012: three informational, never-prescriptive tiers -- see
// docs/client_requirements.md FR-012 and database-design.md §2.7
// (report_assembly_service.classify_recommendations, a first-pass
// keyword heuristic, ASM-007, not yet client-confirmed).
const TIERS: { key: keyof ReportFullContent["recommendations"]; label: string }[] = [
  { key: "at_home", label: "At-Home / Lifestyle" },
  { key: "otc_skincare", label: "OTC / Skincare-Active" },
  { key: "in_clinic", label: "In-Clinic (Optional)" },
]

/**
 * "Protocol" ToC entry (Milestone 2 frontend scope) -- renders the report's
 * existing tiered recommendations, which predate this module but were
 * never surfaced in the UI. Best-effort content per report_enrichment's
 * plans.md decision 6: built against the closest sibling pattern, no
 * confirmed reference screen for this exact page.
 */
export function ProtocolSection({ full }: { full: ReportFullContent }) {
  const hasAnyTier = TIERS.some((tier) => full.recommendations[tier.key]?.length > 0)

  return (
    <motion.div
      id="protocol"
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className="scroll-mt-24 space-y-5 rounded-2xl p-6 shadow-sm"
      style={{ backgroundColor: meridian.surface.card }}
    >
      <h2 className="text-[15px] font-semibold tracking-tight" style={{ color: meridian.ink.primary }}>
        Recommended Protocol
      </h2>

      {hasAnyTier ? (
        <div className="grid gap-4 sm:grid-cols-3">
          {TIERS.map((tier) => {
            const items = full.recommendations[tier.key] ?? []
            if (items.length === 0) return null
            return (
              <div key={tier.key} className="space-y-2 rounded-xl p-4" style={{ backgroundColor: meridian.surface.recessed }}>
                <h3 className="text-xs font-semibold tracking-[0.08em] uppercase" style={{ color: meridian.accent.secondary }}>
                  {tier.label}
                </h3>
                <ul className="space-y-3">
                  {items.map((item, index) => (
                    <ProtocolItemRow key={`${item.text}-${index}`} item={item} />
                  ))}
                </ul>
              </div>
            )
          })}
        </div>
      ) : (
        <p className="text-sm" style={{ color: meridian.ink.muted }}>
          No specific protocol recommendations were generated for this report.
        </p>
      )}

      {full.closing_recommendations ? (
        <p className="text-sm leading-relaxed" style={{ color: meridian.ink.muted }}>
          {full.closing_recommendations}
        </p>
      ) : null}

      <div className="border-t pt-4" style={{ borderColor: meridian.surface.recessed }}>
        <h3 className="text-xs font-semibold tracking-[0.1em] uppercase" style={{ color: meridian.ink.primary }}>
          Disclaimer
        </h3>
        <p className="mt-2 text-xs leading-relaxed" style={{ color: meridian.ink.muted }}>
          {full.limitations}
        </p>
      </div>
    </motion.div>
  )
}
