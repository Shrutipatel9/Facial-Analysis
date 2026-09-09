"use client"

import { ArrowRight, Camera, FileText, Gauge, ListChecks, ScanFace, ShieldCheck, Sparkles } from "lucide-react"
import { motion } from "motion/react"
import Link from "next/link"

import { FacialScanVisual } from "@/components/auth/FacialScanVisual"
import { AuroraBackground } from "@/components/branding/AuroraBackground"
import { Logo } from "@/components/branding/Logo"
import { Button } from "@/components/ui/button"

const FEATURES = [
  { icon: ScanFace, label: "11-feature facial analysis" },
  { icon: Gauge, label: "Computer-vision precision" },
  { icon: ShieldCheck, label: "Private and secure by design" },
] as const

const STEPS = [
  {
    icon: ListChecks,
    title: "Answer a few questions",
    description: "A short questionnaire about your goals and preferences sets the context for your analysis.",
  },
  {
    icon: Camera,
    title: "Upload your photos",
    description: "Front, left, and right angle photos, validated on the spot so every one is analysis-ready.",
  },
  {
    icon: Sparkles,
    title: "AI-powered analysis",
    description: "Computer-vision measurements combined with AI narrative review, feature by feature.",
  },
  {
    icon: FileText,
    title: "Get your report",
    description: "An 11-feature report you can revisit anytime, with a downloadable PDF of the full breakdown.",
  },
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
 * consistency. The "How it works" section below the hero reuses the same
 * step order as the actual product guard chain (questionnaire -> photos ->
 * analysis -> report, see (protected)/layout.tsx) so it's an accurate
 * preview, not just marketing copy.
 */
export function LandingPage() {
  return (
    <div className="min-h-svh bg-background">
      <div className="relative overflow-hidden bg-primary">
        <AuroraBackground />

        <div className="relative flex min-h-svh flex-col">
          <header className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-8">
            <Logo variant="inverted" size="md" />
            <Button
              variant="ghost"
              className="h-10 rounded-full border border-white/20 bg-white/10 px-5 text-primary-foreground backdrop-blur-sm hover:bg-white/20 hover:text-primary-foreground"
              render={<Link href="/signup" />}
              nativeButton={false}
            >
              Sign up
            </Button>
          </header>

          <main className="mx-auto grid w-full max-w-6xl flex-1 grid-cols-1 items-center gap-10 px-6 pb-20 lg:grid-cols-[1.05fr_0.95fr] lg:gap-6">
            <div className="flex flex-col">
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
                <Button
                  size="lg"
                  className="h-12 rounded-full bg-white px-8 text-base text-primary shadow-md hover:bg-white/90 hover:text-primary"
                  render={<Link href="/signup" />}
                  nativeButton={false}
                >
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
            </div>

            <motion.div
              initial={{ opacity: 0, scale: 0.94 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.6, delay: 0.15, ease: "easeOut" }}
              className="hidden justify-center lg:flex"
            >
              <FacialScanVisual className="h-[min(62vh,480px)] w-auto" tone="onBrand" />
            </motion.div>
          </main>
        </div>
      </div>

      <section className="mx-auto w-full max-w-6xl px-6 py-20 sm:py-24">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="mx-auto max-w-2xl text-center"
        >
          <span className="text-xs font-medium tracking-[0.22em] text-primary/70 uppercase">How it works</span>
          <h2 className="mt-3 font-heading text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
            From questions to report, in four steps
          </h2>
          <p className="mt-3 text-base text-muted-foreground text-pretty">
            The same flow you&apos;ll walk through after signing up — no surprises.
          </p>
        </motion.div>

        <div className="relative mt-14 grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4">
          <div
            className="pointer-events-none absolute top-8 right-[12.5%] left-[12.5%] hidden h-px bg-gradient-to-r from-transparent via-primary/25 to-transparent lg:block"
            aria-hidden
          />

          {STEPS.map(({ icon: Icon, title, description }, index) => (
            <motion.div
              key={title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.45, delay: index * 0.1, ease: "easeOut" }}
              whileHover={{ y: -4 }}
              className="group relative flex flex-col items-center gap-4 rounded-2xl border border-border bg-card px-6 py-8 text-center transition-shadow hover:shadow-lg hover:shadow-primary/[0.06]"
            >
              <span className="relative flex size-14 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary transition-transform duration-300 group-hover:scale-110">
                <Icon className="size-6" />
                <span className="absolute -top-2 -right-2 flex size-6 items-center justify-center rounded-full bg-primary text-[11px] font-semibold text-primary-foreground">
                  {index + 1}
                </span>
              </span>
              <h3 className="font-heading text-base font-semibold tracking-tight">{title}</h3>
              <p className="text-sm leading-relaxed text-muted-foreground text-pretty">{description}</p>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-40px" }}
          transition={{ duration: 0.45, delay: 0.2, ease: "easeOut" }}
          className="mt-16 flex justify-center"
        >
          <Button size="lg" className="h-12 px-6 text-base" render={<Link href="/signup" />} nativeButton={false}>
            Start your analysis
            <ArrowRight />
          </Button>
        </motion.div>
      </section>
    </div>
  )
}
