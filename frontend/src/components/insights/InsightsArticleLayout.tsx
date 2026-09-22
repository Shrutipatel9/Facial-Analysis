"use client"

import { ArrowLeft, ArrowRight } from "lucide-react"
import { motion } from "motion/react"
import Link from "next/link"

import { Logo } from "@/components/branding/Logo"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { ArticleCategory } from "@/lib/insights/articles"

interface InsightsArticleLayoutProps {
  title: string
  category: ArticleCategory
  children: React.ReactNode
}

/**
 * FR-031 (Milestone 4) -- shared shell for every /insights/<slug> article
 * page, so each one only needs to supply its own title/category/prose
 * content. Public page (no auth), reuses the same Logo/Button/motion
 * fade-up conventions as LandingPage.tsx rather than the protected app's
 * AppNavbar.tsx (not applicable to a signed-out surface).
 */
export function InsightsArticleLayout({ title, category, children }: InsightsArticleLayoutProps) {
  return (
    <div className="min-h-svh bg-background">
      <header className="mx-auto flex w-full max-w-3xl items-center justify-between px-6 py-8">
        <Logo size="md" />
        <Button variant="outline" size="sm" render={<Link href="/signup" />} nativeButton={false}>
          Get started
        </Button>
      </header>

      <motion.main
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className="mx-auto w-full max-w-3xl px-6 pb-20"
      >
        <Link
          href="/insights"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="size-3.5" />
          Insights
        </Link>

        <div className="mt-6 space-y-3">
          <Badge variant="secondary">{category}</Badge>
          <h1 className="font-heading text-3xl font-semibold tracking-tight text-balance sm:text-4xl">{title}</h1>
        </div>

        <article className="prose-insights mt-10">{children}</article>

        <div className="mt-16 flex flex-col items-center gap-4 rounded-2xl border border-border bg-card px-6 py-10 text-center">
          <h2 className="font-heading text-xl font-semibold tracking-tight">See what your own report shows</h2>
          <p className="max-w-sm text-sm text-muted-foreground text-pretty">
            A measurement-driven analysis of your own face, reviewed feature by feature.
          </p>
          <Button size="lg" className="h-11 px-6" render={<Link href="/signup" />} nativeButton={false}>
            Get started
            <ArrowRight />
          </Button>
        </div>
      </motion.main>
    </div>
  )
}
