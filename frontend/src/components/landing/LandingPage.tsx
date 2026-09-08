"use client"

import { ArrowRight, Gauge, ScanFace, ShieldCheck } from "lucide-react"
import { motion } from "motion/react"
import Link from "next/link"

import { AuroraBackground } from "@/components/branding/AuroraBackground"
import { Logo } from "@/components/branding/Logo"
import { Button } from "@/components/ui/button"

const FEATURES = [
  { icon: ScanFace, label: "11-feature facial analysis" },
  { icon: Gauge, label: "Computer-vision precision" },
  { icon: ShieldCheck, label: "Private and secure by design" },
] as const

const FADE_UP = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
}

/**
 * FR-001: a single, clear CTA into signup. No client content exists for
 * this page (CON-003) -- structure/copy below is a [Recommendation], left
 * to the delivery team. Visual language (gradient/aurora panel, dot-grid,
 * feature row) is drawn from components/auth/AuthLayout.tsx for
 * consistency, but built fresh -- a full-width hero doesn't fit that
 * component's two-column split shape.
 */
export function LandingPage() {
  return (
    <div className="relative min-h-svh overflow-hidden bg-primary">
      <AuroraBackground />

      <div className="relative flex min-h-svh flex-col">
        <header className="mx-auto flex w-full max-w-5xl items-center px-6 py-8">
          <Logo variant="inverted" size="md" />
        </header>

        <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col justify-center px-6 pb-20">
          <motion.span
            {...FADE_UP}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className="mb-6 inline-flex w-fit items-center rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs font-medium tracking-wide text-primary-foreground/90 uppercase backdrop-blur-sm"
          >
            AI-Powered Analysis
          </motion.span>

          <motion.h1
            {...FADE_UP}
            transition={{ duration: 0.5, delay: 0.1, ease: "easeOut" }}
            className="max-w-2xl text-4xl font-medium leading-tight text-primary-foreground text-balance sm:text-5xl"
          >
            Precision facial analysis, powered by computer vision — built for clarity, not guesswork.
          </motion.h1>

          <motion.p
            {...FADE_UP}
            transition={{ duration: 0.5, delay: 0.2, ease: "easeOut" }}
            className="mt-5 max-w-lg text-base text-primary-foreground/70"
          >
            Answer a few questions, upload a few photos, and get a measurement-driven report reviewed
            feature by feature — not a generic beauty score.
          </motion.p>

          <motion.div
            {...FADE_UP}
            transition={{ duration: 0.5, delay: 0.3, ease: "easeOut" }}
            className="mt-9"
          >
            <Button size="lg" className="h-12 px-6 text-base" render={<Link href="/signup" />} nativeButton={false}>
              Get started
              <ArrowRight />
            </Button>
          </motion.div>

          <motion.ul
            initial="initial"
            animate="animate"
            transition={{ staggerChildren: 0.08, delayChildren: 0.45 }}
            className="mt-14 flex flex-wrap gap-x-8 gap-y-3 border-t border-white/15 pt-8"
          >
            {FEATURES.map(({ icon: Icon, label }) => (
              <motion.li
                key={label}
                variants={FADE_UP}
                transition={{ duration: 0.4, ease: "easeOut" }}
                className="flex items-center gap-3 text-sm text-primary-foreground/85"
              >
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-white/10">
                  <Icon className="size-3.5" />
                </span>
                {label}
              </motion.li>
            ))}
          </motion.ul>
        </main>
      </div>
    </div>
  )
}
