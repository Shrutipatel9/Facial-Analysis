import { Compass } from "lucide-react"
import type { Metadata } from "next"
import Link from "next/link"

import { Logo } from "@/components/branding/Logo"
import { Button } from "@/components/ui/button"

export const metadata: Metadata = {
  title: "Page not found",
}

/**
 * Milestone 3.1, Phase 24 (production hardening) -- previously there was no
 * not-found.tsx anywhere in the app, so a bad URL fell through to Next's
 * bare default page. A server component (no interactivity needed) at the
 * root, so it covers every route this app doesn't otherwise match.
 */
export default function NotFound() {
  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-6 bg-background px-4 py-16 text-center">
      <Logo size="md" />
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-muted">
        <Compass className="h-6 w-6 text-muted-foreground" />
      </div>
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Page not found</h1>
        <p className="max-w-sm text-sm text-muted-foreground">
          The page you&apos;re looking for doesn&apos;t exist, or may have moved.
        </p>
      </div>
      <Button render={<Link href="/" />} nativeButton={false}>
        Back to home
      </Button>
    </div>
  )
}
