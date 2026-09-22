/**
 * FR-031 (Milestone 4) -- the Insights hub's article index. Hardcoded,
 * version-controlled content array, same convention as LandingPage.tsx's
 * FEATURES/STEPS and BenefitsSection.tsx's BENEFITS -- no MDX/CMS exists
 * in this codebase, and none is introduced for this.
 *
 * Each article's actual body lives in its own page at
 * app/insights/<slug>/page.tsx -- this array only drives the index page's
 * grid/filter and sitemap.ts's entries, so it stays in sync with the
 * folder-per-article routes manually (there are only a handful of
 * articles; a generated registry would be premature for this scale).
 *
 * Content discipline (milestone4_requirements.md §4's Explicit
 * Non-Goals): every article either explains something this product
 * already computes, or covers a general, uncontroversial facial-
 * aesthetics concept. No procedure/treatment content, no competitor
 * comparisons, no fabricated statistics or quotes.
 */
export const ARTICLE_CATEGORIES = ["Using FaceIQ", "Facial Aesthetics Concepts"] as const

export type ArticleCategory = (typeof ARTICLE_CATEGORIES)[number]

export interface ArticleSummary {
  slug: string
  title: string
  category: ArticleCategory
  excerpt: string
}

export const ARTICLES: ArticleSummary[] = [
  {
    slug: "understanding-your-harmony-score",
    title: "Understanding Your Harmony Score",
    category: "Using FaceIQ",
    excerpt: "What the harmony score on your report actually measures, and what it deliberately isn't.",
  },
  {
    slug: "the-eleven-features-we-analyze",
    title: "The 11 Features We Analyze, and Why We Chose Them",
    category: "Using FaceIQ",
    excerpt: "How FaceIQ's report is structured, and the reasoning behind a fixed 11-feature breakdown.",
  },
  {
    slug: "how-to-take-analysis-photos",
    title: "How to Take Photos That Give You the Most Accurate Analysis",
    category: "Using FaceIQ",
    excerpt: "The lighting, angle, and framing that actually affects measurement accuracy -- straight from our own validation checks.",
  },
  {
    slug: "facial-symmetry-and-proportion-explained",
    title: "Facial Symmetry and Proportion, Explained",
    category: "Facial Aesthetics Concepts",
    excerpt: "What symmetry and proportion actually mean in facial aesthetics, beyond the buzzwords.",
  },
  {
    slug: "what-is-facial-prototypicality",
    title: "What Is Facial Prototypicality (and Why It's Not About Looking 'Normal')",
    category: "Facial Aesthetics Concepts",
    excerpt: "A real perception-research concept, explained without the judgment the name might suggest.",
  },
]
