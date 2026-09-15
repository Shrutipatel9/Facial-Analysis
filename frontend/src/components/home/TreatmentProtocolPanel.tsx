import type { ReportFullContent } from "@/lib/reports/reportApi"

const PHASES: {
  key: keyof ReportFullContent["recommendations"]
  number: string
  title: string
  subtitle: string
  hint: string
  // report_design_spec.md v3.0 §14/report_template.md v3.0 §3.7 -- "a
  // closing paragraph synthesizing why this phase comes first," in
  // prose. Standing, structural copy about phase *sequencing* (same
  // register as the Understanding-the-Results principles), not a
  // per-report finding -- the specific bullet items above it are what
  // carry the actual per-report, finding-traceable content.
  rationale: string
}[] = [
  {
    key: "at_home",
    number: "01",
    title: "Foundation",
    subtitle: "Topicals, hydration, and daily care",
    hint: "Start here",
    rationale:
      "This phase comes first because it's the lowest-risk, highest-leverage starting point — daily " +
      "habits that support the effectiveness of every later phase, not a placeholder to skip.",
  },
  {
    key: "otc_skincare",
    number: "02",
    title: "Active Care",
    subtitle: "Targeted over-the-counter support",
    hint: "Next",
    rationale:
      "Once the foundation is in place, targeted over-the-counter products can address specific " +
      "findings more directly — sequenced second so the basics are already supporting them.",
  },
  {
    key: "in_clinic",
    number: "03",
    title: "Professional Options",
    subtitle: "Discuss with a qualified clinician",
    hint: "If desired",
    rationale:
      "This phase is optional and comes last — worth discussing with a qualified professional only " +
      "if you want to go further than the first two phases, never a required next step.",
  },
]

/**
 * Right-column Treatment Protocol (report_design_spec.md v3.0 §14) --
 * real recommendation buckets only, no fabricated phase durations. Exactly
 * 3 phases, one per existing recommendation tier (at_home/otc_skincare/
 * in_clinic) -- matches the client reference's own phase count for this
 * build, per the report redesign plan.
 */
export function TreatmentProtocolPanel({ full }: { full: ReportFullContent }) {
  const hasAnyPhase = PHASES.some((phase) => full.recommendations[phase.key]?.length > 0)

  return (
    <div className="flex h-fit w-full flex-col gap-4 rounded-2xl border border-border/80 bg-card p-5 shadow-[0_10px_30px_-18px_rgba(20,55,75,0.28)]">
      <h2 className="font-heading text-base font-semibold tracking-tight">Treatment Protocol</h2>

      {!hasAnyPhase ? (
        <p className="text-sm text-muted-foreground">
          No specific protocol recommendations were generated for this report.
        </p>
      ) : (
        <div className="space-y-5">
          {PHASES.map((phase) => {
            const items = full.recommendations[phase.key] ?? []
            if (items.length === 0) return null
            return (
              <section key={phase.key} className="space-y-2.5">
                <div className="space-y-1">
                  <span className="inline-flex rounded-md bg-primary px-2 py-0.5 text-[10px] font-semibold tracking-[0.08em] text-primary-foreground uppercase">
                    Phase {phase.number}
                  </span>
                  <h3 className="text-sm font-semibold text-foreground">
                    {phase.title}: {phase.subtitle}
                  </h3>
                  <p className="text-xs text-muted-foreground">{phase.hint}</p>
                </div>
                <ul className="space-y-2">
                  {items.map((item) => (
                    <li key={item} className="text-sm leading-relaxed text-muted-foreground">
                      {item}
                    </li>
                  ))}
                </ul>
                <p className="text-xs leading-relaxed text-muted-foreground/90">{phase.rationale}</p>
              </section>
            )
          })}
        </div>
      )}
    </div>
  )
}
