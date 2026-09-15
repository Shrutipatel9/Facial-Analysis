"use client"

import { AlertCircle } from "lucide-react"
import { useRouter } from "next/navigation"

import { AiVisualsLayout } from "./AiVisualsLayout"
import { Button } from "@/components/ui/button"
import { useAnalysisStore } from "@/store/analysisStore"

/**
 * Reached via the persistent header nav's "AI Visuals" link (AppNavbar), not
 * the forced onboarding-guard chain -- same posture as /report (see
 * ReportScreen.tsx). The "analysis must be completed" precondition reuses
 * useAnalysisStore directly rather than an extra network call: every
 * protected route already runs useAnalysisGuard before rendering any
 * children, so `status` is guaranteed non-null by the time this component
 * mounts.
 */
export function AiVisualsScreen() {
  const router = useRouter()
  const status = useAnalysisStore((state) => state.status)

  if (status !== "completed") {
    return (
      <div className="flex h-full min-h-0 flex-1 flex-col items-center justify-center gap-4 px-6 py-16 text-center">
        <span className="flex size-14 items-center justify-center rounded-full bg-destructive/10 text-destructive">
          <AlertCircle className="size-6" />
        </span>
        <h1 className="font-sans text-2xl font-semibold tracking-tight">AI Visuals not available yet</h1>
        <p className="max-w-md text-base leading-relaxed text-muted-foreground">
          Finish your facial analysis first to unlock AI-generated hairstyle, outfit, and aging previews.
        </p>
        <Button type="button" variant="outline" className="h-10 rounded-full px-6" onClick={() => router.push("/home")}>
          Back to home
        </Button>
      </div>
    )
  }

  return <AiVisualsLayout />
}
