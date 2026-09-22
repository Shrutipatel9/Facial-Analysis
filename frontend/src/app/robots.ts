import type { MetadataRoute } from "next"

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"

/**
 * Milestone 3.1, Phase 24 (production hardening) -- previously no
 * robots.txt existed at all. The public landing page (`/`) and, since
 * Milestone 4's Phase 28, the /insights hub are meant to be indexed;
 * everything under (auth) and (protected) requires a session anyway and
 * has no value as a search result. No explicit /insights allow entry
 * needed -- `allow: "/"` already covers it, only the (auth) paths below
 * are excluded.
 */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/login", "/signup", "/forgot-password", "/reset-password", "/verify-otp"],
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
  }
}
