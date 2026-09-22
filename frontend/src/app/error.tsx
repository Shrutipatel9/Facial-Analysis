"use client"

import { AlertTriangle } from "lucide-react"
import { motion } from "motion/react"
import Link from "next/link"
import { useEffect } from "react"

import { Logo } from "@/components/branding/Logo"
import { Button } from "@/components/ui/button"

/**
 * Milestone 3.1, Phase 24 (production hardening) -- previously there was no
 * error.tsx anywhere in the app, so an unhandled render error fell through
 * to Next's bare default overlay/page. Client Component: required by
 * Next's error-boundary convention (receives `error`/`reset` as props).
 *
 * Never renders error.message/stack to the user -- same "never leak
 * internals" posture as the backend's generic INTERNAL_ERROR handler
 * (Backend/app/main.py). error.digest (Next's own server-side correlation
 * id for this specific error occurrence) is the one thing safe to show,
 * since it identifies the incident without describing it.
 */
export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    // No client-side error-tracking SDK wired in this app yet -- console is
    // the one place a caught render error is surfaced, for local/devtools
    // debugging.
    console.error("Unhandled render error:", error)
  }, [error])

  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-6 bg-background px-4 py-16 text-center">
      <Logo size="md" />
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col items-center gap-6"
      >
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-destructive/10">
          <AlertTriangle className="h-6 w-6 text-destructive" />
        </div>
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Something went wrong</h1>
          <p className="max-w-sm text-sm text-muted-foreground">
            An unexpected error occurred. You can try again, or head back to safety -- nothing you were working on
            has been lost.
          </p>
          {error.digest ? <p className="text-xs text-muted-foreground/70">Reference: {error.digest}</p> : null}
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" render={<Link href="/" />} nativeButton={false}>
            Back to home
          </Button>
          <Button onClick={reset}>Try again</Button>
        </div>
      </motion.div>
    </div>
  )
}
