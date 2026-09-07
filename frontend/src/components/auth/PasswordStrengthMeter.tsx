"use client"

import { motion } from "motion/react"

import { cn } from "@/lib/utils"
import { scorePasswordStrength } from "@/lib/validation"

const LABELS = ["Very weak", "Weak", "Fair", "Good", "Strong"] as const
const BAR_COLOR = ["bg-destructive", "bg-destructive", "bg-amber-500", "bg-amber-500", "bg-success"] as const

interface PasswordStrengthMeterProps {
  password: string
}

export function PasswordStrengthMeter({ password }: PasswordStrengthMeterProps) {
  if (!password) return null
  const score = scorePasswordStrength(password)

  return (
    <div className="mt-2 space-y-1.5" aria-live="polite">
      <div className="flex gap-1" role="presentation">
        {[0, 1, 2, 3].map((segment) => (
          <div key={segment} className="h-1 flex-1 overflow-hidden rounded-full bg-muted">
            <motion.div
              className={cn("h-full rounded-full", BAR_COLOR[score])}
              initial={false}
              animate={{ scaleX: segment < score ? 1 : 0 }}
              style={{ transformOrigin: "left" }}
              transition={{ duration: 0.25, ease: "easeOut" }}
            />
          </div>
        ))}
      </div>
      <p className="text-xs text-muted-foreground">{LABELS[score]}</p>
    </div>
  )
}
