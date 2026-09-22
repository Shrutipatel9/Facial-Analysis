"use client"

import { ArrowRight, BookOpen } from "lucide-react"
import { motion } from "motion/react"
import Link from "next/link"
import { useState } from "react"

import { Logo } from "@/components/branding/Logo"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ARTICLE_CATEGORIES, ARTICLES, type ArticleCategory } from "@/lib/insights/articles"

const FADE_UP = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
}

/**
 * FR-031 (Milestone 4) -- public Insights hub index. Client component
 * (split out from app/insights/page.tsx, which needs to stay a server
 * component for its `metadata` export): the category filter is the only
 * interactivity, kept client-side rather than a query-param/server round
 * trip since the article set is small (see articles.ts) and this is a
 * marketing/education surface, not something that needs to be a
 * shareable filtered URL.
 */
export function InsightsIndexClient() {
  const [activeCategory, setActiveCategory] = useState<ArticleCategory | "All">("All")
  const visible = activeCategory === "All" ? ARTICLES : ARTICLES.filter((a) => a.category === activeCategory)

  return (
    <div className="min-h-svh bg-background">
      <header className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-8">
        <Logo size="md" />
        <Button variant="outline" size="sm" render={<Link href="/signup" />} nativeButton={false}>
          Get started
        </Button>
      </header>

      <main className="mx-auto w-full max-w-6xl px-6 pb-24">
        <motion.div
          initial={FADE_UP.initial}
          animate={FADE_UP.animate}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="mx-auto max-w-2xl text-center"
        >
          <span className="inline-flex items-center gap-1.5 text-xs font-medium tracking-[0.22em] text-primary/70 uppercase">
            <BookOpen className="size-3.5" />
            Insights
          </span>
          <h1 className="mt-3 font-heading text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
            Understanding your analysis
          </h1>
          <p className="mt-3 text-base text-muted-foreground text-pretty">
            Plain-language explainers on what your report measures, and how to get the most accurate one.
          </p>
        </motion.div>

        <div className="mt-10 flex flex-wrap items-center justify-center gap-2">
          <Button
            variant={activeCategory === "All" ? "default" : "outline"}
            size="sm"
            className="rounded-full"
            onClick={() => setActiveCategory("All")}
          >
            All
          </Button>
          {ARTICLE_CATEGORIES.map((category) => (
            <Button
              key={category}
              variant={activeCategory === category ? "default" : "outline"}
              size="sm"
              className="rounded-full"
              onClick={() => setActiveCategory(category)}
            >
              {category}
            </Button>
          ))}
        </div>

        <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {visible.map(({ slug, title, category, excerpt }, index) => (
            <motion.div
              key={slug}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, delay: index * 0.05, ease: "easeOut" }}
              whileHover={{ y: -4 }}
              className="group flex flex-col gap-3 rounded-2xl border border-border bg-card px-6 py-7 transition-shadow hover:shadow-lg hover:shadow-primary/[0.06]"
            >
              <Badge variant="secondary" className="w-fit">
                {category}
              </Badge>
              <Link href={`/insights/${slug}`} className="flex flex-1 flex-col gap-2">
                <h2 className="font-heading text-lg font-semibold tracking-tight text-balance">{title}</h2>
                <p className="flex-1 text-sm leading-relaxed text-muted-foreground text-pretty">{excerpt}</p>
                <span className="mt-2 inline-flex items-center gap-1.5 text-sm font-medium text-primary">
                  Read more
                  <ArrowRight className="size-3.5 transition-transform group-hover:translate-x-0.5" />
                </span>
              </Link>
            </motion.div>
          ))}
        </div>
      </main>
    </div>
  )
}
