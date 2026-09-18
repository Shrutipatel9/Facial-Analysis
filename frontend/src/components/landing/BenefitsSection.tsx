"use client"

import { Compass, Lock, MessageSquareText, Ruler } from "lucide-react"
import { motion } from "motion/react"

const BENEFITS = [
  {
    icon: Ruler,
    title: "Grounded in measurement",
    description: "Every finding traces back to a real computer-vision measurement, not a generic beauty score.",
  },
  {
    icon: MessageSquareText,
    title: "Every finding explained",
    description: "Plain-language context for each measurement, not just a number with no explanation.",
  },
  {
    icon: Lock,
    title: "Your photos stay private",
    description: "Used only to generate your own analysis and report -- never shared or sold.",
  },
  {
    icon: Compass,
    title: "Clarity, not a verdict",
    description: "Informational and observational throughout -- never a judgment about how you look.",
  },
] as const

/**
 * FR-028 (Milestone 3) -- distinct from the existing "How it works" step
 * grid below (that section describes the product flow; this one describes
 * why it's worth using). Same card shell/icon-badge/fade-up pattern as
 * STEPS, minus the sequential numbering since these aren't ordered steps.
 * Copy is FaceIQ's own value-prop framing (a [Recommendation], same
 * caveat as the rest of this page's copy per LandingPage.tsx's own
 * docstring) -- never a third-party quote/stat, so no fabrication risk.
 */
export function BenefitsSection() {
  return (
    <section className="mx-auto w-full max-w-6xl px-6 py-20 sm:py-24">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-80px" }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="mx-auto max-w-2xl text-center"
      >
        <span className="text-xs font-medium tracking-[0.22em] text-primary/70 uppercase">Why FaceIQ</span>
        <h2 className="mt-3 font-heading text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
          Built for clarity, not guesswork
        </h2>
        <p className="mt-3 text-base text-muted-foreground text-pretty">
          What makes a measurement-driven report different from a generic score.
        </p>
      </motion.div>

      <div className="mt-14 grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4">
        {BENEFITS.map(({ icon: Icon, title, description }, index) => (
          <motion.div
            key={title}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.45, delay: index * 0.1, ease: "easeOut" }}
            whileHover={{ y: -4 }}
            className="group flex flex-col items-center gap-4 rounded-2xl border border-border bg-card px-6 py-8 text-center transition-shadow hover:shadow-lg hover:shadow-primary/[0.06]"
          >
            <span className="flex size-14 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary transition-transform duration-300 group-hover:scale-110">
              <Icon className="size-6" />
            </span>
            <h3 className="font-heading text-base font-semibold tracking-tight">{title}</h3>
            <p className="text-sm leading-relaxed text-muted-foreground text-pretty">{description}</p>
          </motion.div>
        ))}
      </div>
    </section>
  )
}
