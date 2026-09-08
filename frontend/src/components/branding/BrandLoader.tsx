"use client"

import { motion } from "motion/react"

import { FacialScanVisual } from "@/components/auth/FacialScanVisual"
import { Logo } from "@/components/branding/Logo"

/**
 * Minimal branded loading state: light-surface scan animation + FaceIQ mark.
 */
export function BrandLoader() {
  return (
    <div className="flex min-h-svh flex-col items-center justify-center bg-background">
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.45, ease: "easeOut" }}
        className="flex flex-col items-center gap-8"
      >
        <FacialScanVisual className="h-[min(52vh,320px)] w-auto" tone="onLight" />
        <Logo href={null} size="lg" />
      </motion.div>
    </div>
  )
}
