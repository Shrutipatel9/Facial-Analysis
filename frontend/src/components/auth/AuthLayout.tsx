"use client"

import { Gauge, ScanFace, ShieldCheck } from "lucide-react"
import { motion } from "motion/react"
import Link from "next/link"
import type { ReactNode } from "react"

interface AuthLayoutProps {
  title: string
  description: string
  children: ReactNode
  footer?: ReactNode
}

const FEATURES = [
  { icon: ScanFace, label: "11-feature facial analysis" },
  { icon: Gauge, label: "Computer-vision precision" },
  { icon: ShieldCheck, label: "Private and secure by design" },
] as const

const FADE_UP = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
}

export function AuthLayout({ title, description, children, footer }: AuthLayoutProps) {
  return (
    <div className="grid min-h-svh lg:grid-cols-2">
      <div className="flex flex-col justify-center px-6 py-12 sm:px-12 lg:px-20">
        <div className="mx-auto w-full max-w-md">
          <Link href="/" className="mb-12 inline-flex items-center gap-2.5 text-2xl font-semibold tracking-tight">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-sm font-bold text-primary-foreground">
              FA
            </span>
            Facial Analysis
          </Link>

          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, ease: "easeOut" }}
          >
            <h1 className="text-3xl font-semibold tracking-tight text-balance">{title}</h1>
            <p className="mt-2.5 text-base text-muted-foreground text-balance">{description}</p>

            <div className="mt-9">{children}</div>

            {footer ? <div className="mt-7 text-center text-base text-muted-foreground">{footer}</div> : null}
          </motion.div>
        </div>
      </div>

      <div className="relative hidden overflow-hidden bg-primary lg:block">
        {/* Base gradient wash. */}
        <div className="absolute inset-0 bg-gradient-to-br from-primary via-primary to-accent" />

        {/* Slowly drifting blurred orbs -- the "aurora" layer that gives the
            panel life without competing with the text on top of it. */}
        <motion.div
          aria-hidden
          className="absolute -left-24 -top-24 h-96 w-96 rounded-full bg-white/25 blur-3xl"
          animate={{ x: [0, 40, 0], y: [0, 30, 0] }}
          transition={{ duration: 16, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          aria-hidden
          className="absolute bottom-0 right-0 h-[28rem] w-[28rem] rounded-full bg-black/20 blur-3xl"
          animate={{ x: [0, -30, 0], y: [0, -40, 0] }}
          transition={{ duration: 20, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          aria-hidden
          className="absolute left-1/3 top-1/2 h-72 w-72 rounded-full bg-white/15 blur-3xl"
          animate={{ x: [0, 25, -15, 0], y: [0, -25, 15, 0] }}
          transition={{ duration: 24, repeat: Infinity, ease: "easeInOut" }}
        />

        {/* Dot-grid texture on top of the orbs. */}
        <div
          className="absolute inset-0 opacity-[0.08]"
          style={{
            backgroundImage: "radial-gradient(circle at 1px 1px, white 1px, transparent 0)",
            backgroundSize: "28px 28px",
          }}
        />

        <div className="relative flex h-full flex-col justify-end p-12 xl:p-16">
          <motion.span
            {...FADE_UP}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className="mb-6 inline-flex w-fit items-center rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs font-medium tracking-wide text-primary-foreground/90 uppercase backdrop-blur-sm"
          >
            AI-Powered Analysis
          </motion.span>

          <motion.p
            {...FADE_UP}
            transition={{ duration: 0.5, delay: 0.1, ease: "easeOut" }}
            className="max-w-md text-2xl font-medium leading-relaxed text-primary-foreground text-balance"
          >
            Precision facial analysis, powered by computer vision — built for clarity, not guesswork.
          </motion.p>

          <motion.p
            {...FADE_UP}
            transition={{ duration: 0.5, delay: 0.2, ease: "easeOut" }}
            className="mt-4 max-w-sm text-sm text-primary-foreground/70"
          >
            Measurement-driven insight, reviewed for every feature.
          </motion.p>

          <motion.ul
            initial="initial"
            animate="animate"
            transition={{ staggerChildren: 0.08, delayChildren: 0.35 }}
            className="mt-10 flex flex-col gap-3 border-t border-white/15 pt-8"
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
      </div>
    </div>
  )
}
