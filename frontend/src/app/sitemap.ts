import type { MetadataRoute } from "next"

import { ARTICLES } from "@/lib/insights/articles"

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"

/**
 * Milestone 3.1, Phase 24 (production hardening) -- previously no sitemap
 * existed at all. Milestone 4, Phase 28 added the /insights hub -- its
 * articles are the second batch of real public content, everything under
 * (auth) and (protected) is still either an auth flow step or requires a
 * session, never something worth a search engine indexing on its own.
 */
export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: SITE_URL,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 1,
    },
    {
      url: `${SITE_URL}/insights`,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.8,
    },
    ...ARTICLES.map(({ slug }) => ({
      url: `${SITE_URL}/insights/${slug}`,
      lastModified: new Date(),
      changeFrequency: "yearly" as const,
      priority: 0.6,
    })),
  ]
}
