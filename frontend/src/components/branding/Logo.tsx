import Link from "next/link"

import { cn } from "@/lib/utils"

interface LogoProps {
  /** Where the logo links to. Pass null to render a static, non-linking mark. */
  href?: string | null
  size?: "sm" | "md" | "lg"
  /** "inverted" for use on the primary/aurora brand surface (AuthLayout's
   * brand panel, the landing page hero) -- "default" for light surfaces
   * (the app header, anywhere else). */
  variant?: "default" | "inverted"
  className?: string
}

const SIZE_CLASSES = {
  sm: "text-lg",
  md: "text-xl",
  lg: "text-3xl sm:text-4xl",
} as const

/**
 * The FaceIQ wordmark -- the platform's only logo. No icon mark by design:
 * the styled name itself is the brand, everywhere a logo would otherwise
 * appear (navbar, auth screens, landing page). Keep this the single place
 * that styling is defined so every surface stays visually identical.
 */
export function Logo({ href = "/", size = "md", variant = "default", className }: LogoProps) {
  const mark = (
    <span
      className={cn(
        "inline-flex items-baseline font-heading font-semibold tracking-tight select-none",
        SIZE_CLASSES[size],
        variant === "inverted" ? "text-primary-foreground" : "text-foreground",
        className
      )}
    >
      Face
      <span className="font-black">IQ</span>
    </span>
  )

  if (!href) return mark

  return (
    <Link
      href={href}
      className="rounded-md outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
      aria-label="FaceIQ home"
    >
      {mark}
    </Link>
  )
}
