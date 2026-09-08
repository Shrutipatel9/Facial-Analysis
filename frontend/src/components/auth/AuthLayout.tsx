"use client"

import { Gauge, ScanFace, ShieldCheck } from "lucide-react"
import { motion } from "motion/react"
import type { ReactNode } from "react"

import { FacialScanVisual } from "@/components/auth/FacialScanVisual"
import { AuroraBackground } from "@/components/branding/AuroraBackground"
import { Logo } from "@/components/branding/Logo"

interface AuthLayoutProps {
  title: string
  description: string
  children: ReactNode
  footer?: ReactNode
}

const FEATURES = [
  { icon: ScanFace, label: "11-feature analysis" },
  { icon: Gauge, label: "CV precision" },
  { icon: ShieldCheck, label: "Private by design" },
] as const

const FADE_UP = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
}

export function AuthLayout({ title, description, children, footer }: AuthLayoutProps) {
  return (
    <div className="grid h-svh overflow-hidden lg:grid-cols-2">
      {/* Form column — scrolls only if the form itself is taller than the viewport */}
      <div className="flex min-h-0 flex-col justify-center overflow-y-auto px-6 py-10 sm:px-12 lg:px-20">
        <div className="mx-auto w-full max-w-md">
          <div className="mb-10">
            <Logo size="lg" />
          </div>

          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, ease: "easeOut" }}
          >
            <h1 className="text-3xl font-semibold tracking-tight text-balance">{title}</h1>
            <p className="mt-2.5 text-base text-muted-foreground text-balance">{description}</p>

            <div className="mt-8">{children}</div>

            {footer ? <div className="mt-6 text-center text-base text-muted-foreground">{footer}</div> : null}
          </motion.div>
        </div>
      </div>

      {/* Brand column — fixed to viewport, no scroll; visual + copy centered */}
      <div className="relative hidden min-h-0 overflow-hidden bg-primary lg:block">
        <AuroraBackground />

        <div className="relative flex h-full flex-col items-center justify-center gap-5 px-10 py-10 xl:px-14">
          <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6, ease: "easeOut" }}
            className="flex w-full shrink justify-center"
          >
            <FacialScanVisual className="h-[min(56vh,400px)] w-auto" />
          </motion.div>

          <div className="w-full max-w-md shrink-0 text-center">
            <motion.span
              {...FADE_UP}
              transition={{ duration: 0.5, ease: "easeOut" }}
              className="mb-4 inline-flex w-fit items-center rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs font-medium tracking-wide text-primary-foreground/90 uppercase"
            >
              AI-Powered Analysis
            </motion.span>

            <motion.p
              {...FADE_UP}
              transition={{ duration: 0.5, delay: 0.08, ease: "easeOut" }}
              className="text-xl font-medium leading-snug text-primary-foreground text-balance xl:text-2xl"
            >
              Precision facial analysis, powered by computer vision.
            </motion.p>

            <motion.ul
              initial="initial"
              animate="animate"
              transition={{ staggerChildren: 0.08, delayChildren: 0.25 }}
              className="mt-6 flex flex-wrap items-center justify-center gap-x-5 gap-y-2"
            >
              {FEATURES.map(({ icon: Icon, label }) => (
                <motion.li
                  key={label}
                  variants={FADE_UP}
                  transition={{ duration: 0.4, ease: "easeOut" }}
                  className="flex items-center gap-2 text-sm text-primary-foreground/85"
                >
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white/10">
                    <Icon className="size-3" />
                  </span>
                  {label}
                </motion.li>
              ))}
            </motion.ul>
          </div>
        </div>
      </div>
    </div>
  )
}
