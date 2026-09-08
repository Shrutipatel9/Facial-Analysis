"use client"

import { motion } from "motion/react"

import { cn } from "@/lib/utils"

/**
 * The shared brand background: gradient wash + drifting blurred orbs +
 * dot-grid texture, on the primary/accent gradient. Used identically on
 * every brand-forward surface (AuthLayout's panel, the landing page hero)
 * so the animation language stays consistent app-wide rather than
 * hand-tuned per screen -- render as an absolutely-positioned first child
 * of a `relative` container, with real content layered on top of it.
 */
export function AuroraBackground({ className }: { className?: string }) {
  return (
    <div className={cn("absolute inset-0 overflow-hidden bg-primary", className)} aria-hidden>
      <div className="absolute inset-0 bg-gradient-to-br from-primary via-primary to-accent" />

      <motion.div
        className="absolute -left-24 -top-24 h-96 w-96 rounded-full bg-white/25 blur-3xl"
        animate={{ x: [0, 40, 0], y: [0, 30, 0] }}
        transition={{ duration: 16, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute bottom-0 right-0 h-[28rem] w-[28rem] rounded-full bg-black/20 blur-3xl"
        animate={{ x: [0, -30, 0], y: [0, -40, 0] }}
        transition={{ duration: 20, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute left-1/3 top-1/2 h-72 w-72 rounded-full bg-white/15 blur-3xl"
        animate={{ x: [0, 25, -15, 0], y: [0, -25, 15, 0] }}
        transition={{ duration: 24, repeat: Infinity, ease: "easeInOut" }}
      />

      <div
        className="absolute inset-0 opacity-[0.08]"
        style={{
          backgroundImage: "radial-gradient(circle at 1px 1px, white 1px, transparent 0)",
          backgroundSize: "28px 28px",
        }}
      />
    </div>
  )
}
